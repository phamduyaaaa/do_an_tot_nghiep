// ==================================================
// Project          : ESP32 Micro-ROS RC Teleop Minimal (Updated)
// Author           : DuyPham
// Date             : 28-11-2025
// Description      : Read RC, map to Twist using CONFIG_H thresholds, publish cmd_vel
// ==================================================
#include <stdio.h>
#include <Arduino.h>
#include <micro_ros_arduino.h>
#include <geometry_msgs/msg/twist.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>

// ===============================================================================
// HẰNG SỐ RC TỪ CONFIGURATION (Được sao chép lại để dễ quản lý)
// ===============================================================================

// RC PINS
const int rcPin2 = 17; // CH2: Throttle F/B
const int rcPin4 = 18; // CH4: Turn L/R
const int rcPin6 = 23; // Ch6: ON/OFF TELEOP

// HYPERPARAMETERS
const float linear_scale = 0.5;   // scale factor for linear.x
const float angular_scale = 3.0;  // scale factor for angular.z

// CH2 (Throttle) - Đã cập nhật theo CONFIG_H
// FORWARD: [1580, 1810]
const uint16_t CH2_FWD_MIN = 1580; 
const uint16_t CH2_FWD_MAX = 1810;
// STOP: [1490, 1570]
const uint16_t CH2_STOP_MIN = 1490; 
const uint16_t CH2_STOP_MAX = 1570;
// BACKWARD: [1280, 1480]
const uint16_t CH2_BWD_MIN = 1280; 
const uint16_t CH2_BWD_MAX = 1480; 

// CH4 (Steering) - Đã cập nhật theo CONFIG_H
// TURN LEFT: [1180, 1390]
const uint16_t CH4_LEFT_MIN = 1180;
const uint16_t CH4_LEFT_MAX = 1390;
// TURN RIGHT: [1510, 1680]
const uint16_t CH4_RIGHT_MIN = 1510;
const uint16_t CH4_RIGHT_MAX = 1680;
// DEADZONE (Giữa): [1391, 1509]
const uint16_t CH4_MID_MIN = 1391; 
const uint16_t CH4_MID_MAX = 1509;
// CH6
const uint16_t CH6_THESHOLD = 1500;

// ---------------- RC VARIABLES ----------------
volatile unsigned long pulseWidth2 = 1500;
volatile unsigned long pulseWidth4 = 1500;
volatile unsigned long pulseWidth6 = 1500;
volatile unsigned long lastTime2 = 0;
volatile unsigned long lastTime4 = 0;
volatile unsigned long lastTime6 = 0;

// ---------------- MICRO-ROS ----------------
rcl_publisher_t cmd_vel_pub;
geometry_msgs__msg__Twist twist_msg;
rcl_node_t node;
rclc_executor_t executor;
rcl_allocator_t allocator;

// Hàm hỗ trợ để giới hạn giá trị float (constrain float)
float constrain_f(float value, float min_val, float max_val) {
    if (value < min_val) return min_val;
    if (value > max_val) return max_val;
    return value;
}


// ===================== INTERRUPTS =====================
void IRAM_ATTR handleInterrupt2() {
  if (digitalRead(rcPin2) == HIGH) lastTime2 = micros();
  else pulseWidth2 = micros() - lastTime2;
}

void IRAM_ATTR handleInterrupt4() {
  if (digitalRead(rcPin4) == HIGH) lastTime4 = micros();
  else pulseWidth4 = micros() - lastTime4;
}

void IRAM_ATTR handleInterrupt6() {
  if (digitalRead(rcPin6) == HIGH) lastTime6 = micros();
  else pulseWidth6 = micros() - lastTime6;
}

// ===================== TASK: READ RC & PUBLISH =====================
void TaskRC(void *pvParameters){
  for(;;){
    unsigned long pw2, pw4, pw6;
    noInterrupts();
    pw2 = pulseWidth2;
    pw4 = pulseWidth4;
    pw6 = pulseWidth6;
    interrupts();

    float linear_x = 0;
    float angular_z = 0;

    // --- ÁNH XẠ CH2 (Linear.x) ---
    if (pw2 >= CH2_STOP_MIN && pw2 <= CH2_STOP_MAX) {
      // Vùng Deadband/STOP
      linear_x = 0.0;
    } 
    else if (pw2 > CH2_STOP_MAX && pw2 <= CH2_FWD_MAX) {
      // Tiến (Forward): Ánh xạ từ [CH2_STOP_MAX, CH2_FWD_MAX] -> [0.0, 1.0]
      linear_x = (float)(pw2 - CH2_STOP_MAX) / (CH2_FWD_MAX - CH2_STOP_MAX);
      linear_x = constrain_f(linear_x, 0.0, 1.0);
    } 
    else if (pw2 >= CH2_BWD_MIN && pw2 < CH2_STOP_MIN) {
      // Lùi (Backward): Ánh xạ từ [CH2_STOP_MIN, CH2_BWD_MIN] -> [0.0, -1.0]
      // Đảo ngược thứ tự để đi từ 0.0 về -1.0
      linear_x = (float)(CH2_STOP_MIN - pw2) / (CH2_STOP_MIN - CH2_BWD_MIN);
      linear_x = -constrain_f(linear_x, 0.0, 1.0);
    }


    // --- ÁNH XẠ CH4 (Angular.z) ---
    if (pw4 >= CH4_MID_MIN && pw4 <= CH4_MID_MAX) {
      // Vùng Deadband/Đi thẳng
      angular_z = 0.0;
    } 
    else if (pw4 > CH4_MID_MAX && pw4 <= CH4_RIGHT_MAX) {
      // Rẽ phải (Turn Right): Ánh xạ từ [CH4_MID_MAX, CH4_RIGHT_MAX] -> [0.0, -1.0] 
      angular_z = (float)(pw4 - CH4_MID_MAX) / (CH4_RIGHT_MAX - CH4_MID_MAX);
      angular_z = -constrain_f(angular_z, 0.0, 1.0); // Rẽ phải (góc âm)
    } 
    else if (pw4 >= CH4_LEFT_MIN && pw4 < CH4_MID_MIN) {
      // Rẽ trái (Turn Left): Ánh xạ từ [CH4_MID_MIN, CH4_LEFT_MIN] -> [0.0, 1.0] 
      angular_z = (float)(CH4_MID_MIN - pw4) / (CH4_MID_MIN - CH4_LEFT_MIN);
      angular_z = constrain_f(angular_z, 0.0, 1.0); // Rẽ trái (góc dương)
    }
    
    // --- ÁP DỤNG SCALES & PUBLISH ---
    
    //CHECK CH6:
    if (pw6 < CH6_THESHOLD){
      twist_msg.linear.x = linear_x * linear_scale;
      twist_msg.linear.y = 0;
      twist_msg.linear.z = 0;
      twist_msg.angular.x = 0;
      twist_msg.angular.y = 0;
      twist_msg.angular.z = angular_z * angular_scale;

      rcl_publish(&cmd_vel_pub, &twist_msg, NULL);
    }
    vTaskDelay(20 / portTICK_PERIOD_MS); // ~50Hz
  }
}

// ===================== SETUP =====================
void setup() {
  //Serial.begin(115200);

  // --- Cấu hình RC ---
  pinMode(rcPin2, INPUT);
  pinMode(rcPin4, INPUT);
  pinMode(rcPin6, INPUT);
  attachInterrupt(digitalPinToInterrupt(rcPin2), handleInterrupt2, CHANGE);
  attachInterrupt(digitalPinToInterrupt(rcPin4), handleInterrupt4, CHANGE);
  attachInterrupt(digitalPinToInterrupt(rcPin6), handleInterrupt6, CHANGE);
  // --- micro-ROS ---
  set_microros_transports();
  allocator = rcl_get_default_allocator();
  rclc_support_t support;
  rclc_support_init(&support, 0, NULL, &allocator);
  
  // Xử lý lỗi khởi tạo micro-ROS
  if (RCL_RET_OK != rclc_node_init_default(&node, "micro_rc_teleop", "", &support)) {
      Serial.println("Node initialization failed!");
      return;
  }
  
  if (RCL_RET_OK != rclc_publisher_init_default(
    &cmd_vel_pub,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
    "cmd_vel"
  )) {
      Serial.println("Publisher initialization failed!");
      return;
  }

  // --- Start Task ---
  // Sử dụng Core 1 cho TaskRC
  xTaskCreatePinnedToCore(TaskRC, "TaskRC", 4096, NULL, 1, NULL, 1);
  //Serial.println("micro_rc_teleop ready and publishing to cmd_vel.");
}

// ===================== LOOP =====================
void loop() {
  // Không làm gì, tất cả xử lý trong TaskRC
}
