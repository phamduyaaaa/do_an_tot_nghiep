#!/bin/bash

# Move to the project directory, exit if it doesn't exist to prevent 
# running streamlit in the wrong location.
cd imitation_learning || exit

echo "Run app.py..."
python3 -m streamlit run app.py
