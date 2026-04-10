// =============================================================================
// Project     : ESP32 Micro-ROS RC Teleop Minimal
// Author      : DuyPham
// Date        : 2025-11-28
// Description : Read RC signals, map to Twist using CONFIG thresholds, publish
//               to cmd_vel topic.
// =============================================================================

#include <Arduino.h>
#include <geometry_msgs/msg/twist.h>
#include <micro_ros_arduino.h>
#include <rcl/error_handling.h>
#include <rcl/rcl.h>
#include <rclc/executor.h>
#include <rclc/rclc.h>
#include <stdio.h>

// =============================================================================
// CONFIGURATION CONSTANTS (From CONFIG_H)
// =============================================================================

// RC PINS
const int RC_PIN_CH2 = 17;  // CH2: Throttle Forward/Backward
const int RC_PIN_CH4 = 18;  // CH4: Steering Left/Right
const int RC_PIN_CH6 = 23;  // CH6: Teleop Enable/Disable

// HYPERPARAMETERS
const float LINEAR_SCALE = 0.5;   // Scale factor for linear.x
const float ANGULAR_SCALE = 3.0;  // Scale factor for angular.z

// CH2 (Throttle) THRESHOLDS
const uint16_t CH2_FWD_MIN = 1580;
const uint16_t CH2_FWD_MAX = 1810;
const uint16_t CH2_STOP_MIN = 1490;
const uint16_t CH2_STOP_MAX = 1570;
const uint16_t CH2_BWD_MIN = 1280;
const uint16_t CH2_BWD_MAX = 1480;

// CH4 (Steering) THRESHOLDS
const uint16_t CH4_LEFT_MIN = 1180;
const uint16_t CH4_LEFT_MAX = 1390;
const uint16_t CH4_RIGHT_MIN = 1510;
const uint16_t CH4_RIGHT_MAX = 1680;
const uint16_t CH4_MID_MIN = 1391;
const uint16_t CH4_MID_MAX = 1509;

// CH6 THRESHOLD
const uint16_t CH6_THRESHOLD = 1500;

// ---------------- RC VARIABLES ----------------
volatile unsigned long pulse_width_ch2 = 1500;
volatile unsigned long pulse_width_ch4 = 1500;
volatile unsigned long pulse_width_ch6 = 1500;
volatile unsigned long last_time_ch2 = 0;
volatile unsigned long last_time_ch4 = 0;
volatile unsigned long last_time_ch6 = 0;

// ---------------- MICRO-ROS GLOBALS ----------------
rcl_publisher_t cmd_vel_pub;
geometry_msgs__msg__Twist twist_msg;
rcl_node_t node;
rcl_allocator_t allocator;

// Helper function to constrain float values
float constrain_f(float value, float min_val, float max_val) {
  if (value < min_val) return min_val;
  if (value > max_val) return max_val;
  return value;
}

// ===================== INTERRUPT SERVICE ROUTINES =====================
void IRAM_ATTR handleInterruptCH2() {
  if (digitalRead(RC_PIN_CH2) == HIGH) {
    last_time_ch2 = micros();
  } else {
    pulse_width_ch2 = micros() - last_time_ch2;
  }
}

void IRAM_ATTR handleInterruptCH4() {
  if (digitalRead(RC_PIN_CH4) == HIGH) {
    last_time_ch4 = micros();
  } else {
    pulse_width_ch4 = micros() - last_time_ch4;
  }
}

void IRAM_ATTR handleInterruptCH6() {
  if (digitalRead(RC_PIN_CH6) == HIGH) {
    last_time_ch6 = micros();
  } else {
    pulse_width_ch6 = micros() - last_time_ch6;
  }
}

// ===================== TASK: READ RC & PUBLISH =====================
void TaskRC(void* pvParameters) {
  for (;;) {
    unsigned long pw2, pw4, pw6;

    // Critical section to read volatile variables
    noInterrupts();
    pw2 = pulse_width_ch2;
    pw4 = pulse_width_ch4;
    pw6 = pulse_width_ch6;
    interrupts();

    float linear_x = 0.0;
    float angular_z = 0.0;

    // --- CH2 MAPPING (Linear.x) ---
    if (pw2 >= CH2_STOP_MIN && pw2 <= CH2_STOP_MAX) {
      linear_x = 0.0;
    } else if (pw2 > CH2_STOP_MAX && pw2 <= CH2_FWD_MAX) {
      // Forward: Map [STOP_MAX, FWD_MAX] -> [0.0, 1.0]
      linear_x = (float)(pw2 - CH2_STOP_MAX) / (CH2_FWD_MAX - CH2_STOP_MAX);
      linear_x = constrain_f(linear_x, 0.0, 1.0);
    } else if (pw2 >= CH2_BWD_MIN && pw2 < CH2_STOP_MIN) {
      // Backward: Map [STOP_MIN, BWD_MIN] -> [0.0, -1.0]
      linear_x = (float)(CH2_STOP_MIN - pw2) / (CH2_STOP_MIN - CH2_BWD_MIN);
      linear_x = -constrain_f(linear_x, 0.0, 1.0);
    }

    // --- CH4 MAPPING (Angular.z) ---
    if (pw4 >= CH4_MID_MIN && pw4 <= CH4_MID_MAX) {
      angular_z = 0.0;
    } else if (pw4 > CH4_MID_MAX && pw4 <= CH4_RIGHT_MAX) {
      // Turn Right: Map [MID_MAX, RIGHT_MAX] -> [0.0, -1.0]
      angular_z = (float)(pw4 - CH4_MID_MAX) / (CH4_RIGHT_MAX - CH4_MID_MAX);
      angular_z = -constrain_f(angular_z, 0.0, 1.0);
    } else if (pw4 >= CH4_LEFT_MIN && pw4 < CH4_MID_MIN) {
      // Turn Left: Map [MID_MIN, LEFT_MIN] -> [0.0, 1.0]
      angular_z = (float)(CH4_MID_MIN - pw4) / (CH4_MID_MIN - CH4_LEFT_MIN);
      angular_z = constrain_f(angular_z, 0.0, 1.0);
    }

    // --- PUBLISH MSG IF CH6 IS ACTIVE ---
    if (pw6 < CH6_THRESHOLD) {
      twist_msg.linear.x = linear_x * LINEAR_SCALE;
      twist_msg.linear.y = 0.0;
      twist_msg.linear.z = 0.0;
      twist_msg.angular.x = 0.0;
      twist_msg.angular.y = 0.0;
      twist_msg.angular.z = angular_z * ANGULAR_SCALE;

      rcl_publish(&cmd_vel_pub, &twist_msg, NULL);
    }

    vTaskDelay(pdMS_TO_TICKS(20));  // 50Hz frequency
  }
}

// ===================== SETUP =====================
void setup() {
  // RC Pin configuration
  pinMode(RC_PIN_CH2, INPUT);
  pinMode(RC_PIN_CH4, INPUT);
  pinMode(RC_PIN_CH6, INPUT);

  attachInterrupt(digitalPinToInterrupt(RC_PIN_CH2), handleInterruptCH2, CHANGE);
  attachInterrupt(digitalPinToInterrupt(RC_PIN_CH4), handleInterruptCH4, CHANGE);
  attachInterrupt(digitalPinToInterrupt(RC_PIN_CH6), handleInterruptCH6, CHANGE);

  // Micro-ROS initialization
  set_microros_transports();
  allocator = rcl_get_default_allocator();

  rclc_support_t support;
  rclc_support_init(&support, 0, NULL, &allocator);

  // Node initialization
  if (rclc_node_init_default(&node, "micro_rc_teleop", "", &support) !=
      RCL_RET_OK) {
    return;
  }

  // Publisher initialization
  const rosidl_message_type_support_t* type_support =
      ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist);

  if (rclc_publisher_init_default(&cmd_vel_pub, &node, type_support,
                                  "cmd_vel") != RCL_RET_OK) {
    return;
  }

  // Create Task on Core 1
  xTaskCreatePinnedToCore(TaskRC, "TaskRC", 4096, NULL, 1, NULL, 1);
}

// ===================== LOOP =====================
void loop() {
  // All processing is handled in TaskRC
  delay(100);
}
