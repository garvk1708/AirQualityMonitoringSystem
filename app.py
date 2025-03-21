import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import random
from datetime import datetime, timedelta
import air_quality_utils as aq_utils

# Page configuration
st.set_page_config(
    page_title="Air Quality Monitoring Dashboard",
    page_icon="🌬️",
    layout="wide",
)

# ESP8266 IP address - can be changed in the sidebar
ESP_IP = "http://192.168.137.91/data"

# Initialize session state variables to store historical data
if 'timestamps' not in st.session_state:
    st.session_state.timestamps = []
if 'temperatures' not in st.session_state:
    st.session_state.temperatures = []
if 'humidities' not in st.session_state:
    st.session_state.humidities = []
if 'air_qualities' not in st.session_state:
    st.session_state.air_qualities = []
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now() - timedelta(minutes=10)
if 'connection_error' not in st.session_state:
    st.session_state.connection_error = False
if 'error_message' not in st.session_state:
    st.session_state.error_message = ""
if 'demo_mode' not in st.session_state:
    st.session_state.demo_mode = False
if 'base_temp' not in st.session_state:
    st.session_state.base_temp = 24.5
if 'base_humidity' not in st.session_state:
    st.session_state.base_humidity = 48.0
if 'base_air_quality' not in st.session_state:
    st.session_state.base_air_quality = 150

# Application title
st.title("Air Quality Monitoring Dashboard")

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    
    # ESP IP address input
    esp_ip_input = st.text_input(
        "ESP8266 IP Address",
        value=ESP_IP.replace("http://", "").replace("/data", "")
    )
    ESP_IP = f"http://{esp_ip_input}/data"
    
    st.write("---")
    
    # Demo mode toggle
    st.session_state.demo_mode = st.checkbox("Demo Mode (Generate Sample Data)", value=True)
    
    st.write("---")
    
    # Update frequency slider
    update_frequency = st.slider(
        "Update Frequency (seconds)",
        min_value=3,
        max_value=60,
        value=5,
        step=1
    )
    
    st.write("---")
    
    # Data history slider
    data_history = st.slider(
        "Data History (points)",
        min_value=10,
        max_value=1000,
        value=100,
        step=10
    )
    
    st.write("---")
    
    # Prediction settings
    predict_points = st.slider(
        "Prediction Points",
        min_value=1,
        max_value=20,
        value=5,
        step=1
    )
    
    # Refresh data button
    if st.button("Refresh Data Now"):
        st.session_state.last_update = datetime.now() - timedelta(minutes=10)

# Function to generate simulated data
def generate_sample_data():
    # Generate slightly varying data around base values
    # This simulates real sensor readings with some natural variation
    temp_variation = random.uniform(-0.5, 0.5)
    humidity_variation = random.uniform(-2.0, 2.0)
    air_quality_variation = random.uniform(-10, 10)
    
    # Update base values with some drift to simulate changing conditions
    st.session_state.base_temp += random.uniform(-0.1, 0.1)
    st.session_state.base_humidity += random.uniform(-0.2, 0.2)
    st.session_state.base_air_quality += random.uniform(-5, 5)
    
    # Keep values in realistic ranges
    st.session_state.base_temp = max(18, min(30, st.session_state.base_temp))
    st.session_state.base_humidity = max(30, min(70, st.session_state.base_humidity))
    st.session_state.base_air_quality = max(50, min(500, st.session_state.base_air_quality))
    
    # Return simulated data
    return {
        "temperature": st.session_state.base_temp + temp_variation,
        "humidity": st.session_state.base_humidity + humidity_variation,
        "airQuality": int(st.session_state.base_air_quality + air_quality_variation)
    }

# Function to fetch data from ESP8266 or generate sample data
def fetch_data():
    if st.session_state.demo_mode:
        # Generate sample data in demo mode
        sample_data = generate_sample_data()
        st.session_state.connection_error = False
        return sample_data
    else:
        # Try to fetch real data from ESP8266
        try:
            response = requests.get(ESP_IP, timeout=5)
            data = response.json()
            st.session_state.connection_error = False
            return data
        except Exception as e:
            st.session_state.connection_error = True
            st.session_state.error_message = f"Error fetching data: {e}"
            return None

# Main dashboard layout
col1, col2, col3 = st.columns(3)

# Current time display
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.write(f"**Dashboard updated at:** {current_time}")

# Check if it's time to update
time_since_update = (datetime.now() - st.session_state.last_update).total_seconds()
if time_since_update >= update_frequency:
    with st.spinner("Fetching latest sensor data..."):
        sensor_data = fetch_data()
        
        if sensor_data:
            # Update successful
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Limit data history
            if len(st.session_state.timestamps) >= data_history:
                st.session_state.timestamps.pop(0)
                st.session_state.temperatures.pop(0)
                st.session_state.humidities.pop(0)
                st.session_state.air_qualities.pop(0)
            
            # Add new data
            st.session_state.timestamps.append(current_time)
            st.session_state.temperatures.append(sensor_data["temperature"])
            st.session_state.humidities.append(sensor_data["humidity"])
            st.session_state.air_qualities.append(sensor_data["airQuality"])
            
            # Update last update time
            st.session_state.last_update = datetime.now()

# Display connection error if any
if st.session_state.connection_error:
    st.error(f"Cannot connect to ESP8266 device. {st.session_state.error_message}")
    if len(st.session_state.timestamps) == 0:
        st.warning("No historical data available. Please check the device connection.")
        st.stop()

# Display current readings in columns with metrics
if len(st.session_state.timestamps) > 0:
    with col1:
        current_temp = st.session_state.temperatures[-1]
        st.metric(
            "Temperature",
            f"{current_temp:.1f} °C",
            delta=f"{current_temp - st.session_state.temperatures[-2]:.1f} °C" if len(st.session_state.temperatures) > 1 else None
        )
        temp_status = aq_utils.interpret_temperature(current_temp)
        st.info(f"Status: {temp_status}")
        
    with col2:
        current_hum = st.session_state.humidities[-1]
        st.metric(
            "Humidity",
            f"{current_hum:.1f} %",
            delta=f"{current_hum - st.session_state.humidities[-2]:.1f} %" if len(st.session_state.humidities) > 1 else None
        )
        humidity_status = aq_utils.interpret_humidity(current_hum)
        st.info(f"Status: {humidity_status}")
        
    with col3:
        current_aq = st.session_state.air_qualities[-1]
        st.metric(
            "Air Quality",
            f"{current_aq} PPM",
            delta=f"{current_aq - st.session_state.air_qualities[-2]} PPM" if len(st.session_state.air_qualities) > 1 else None,
            delta_color="inverse"  # Lower is better for air quality
        )
        air_quality_status, air_quality_message = aq_utils.interpret_air_quality(current_aq)
        st.info(f"Status: {air_quality_status}")

    # Create a DataFrame for historical data
    df = pd.DataFrame({
        "Time": st.session_state.timestamps,
        "Temperature (°C)": st.session_state.temperatures,
        "Humidity (%)": st.session_state.humidities,
        "Air Quality (PPM)": st.session_state.air_qualities
    })

    # Add prediction data if we have enough historical data
    if len(df) >= 5:  # Need some data for prediction
        # Create prediction dataframe
        pred_df = aq_utils.generate_predictions(df, predict_points)
        
        # Add tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["All Metrics", "Temperature", "Humidity", "Air Quality"])
        
        with tab1:
            st.subheader("All Metrics Over Time")
            st.line_chart(df.set_index("Time")[["Temperature (°C)", "Humidity (%)", "Air Quality (PPM)"]])
            
            # Show predictions
            st.subheader("Predictions for Next Data Points")
            st.line_chart(pred_df)
        
        with tab2:
            st.subheader("Temperature Over Time")
            st.line_chart(df.set_index("Time")["Temperature (°C)"])
            
            # Show only temperature prediction
            temp_pred_df = pred_df[["Temperature (°C)"]]
            st.subheader("Temperature Prediction")
            st.line_chart(temp_pred_df)
        
        with tab3:
            st.subheader("Humidity Over Time")
            st.line_chart(df.set_index("Time")["Humidity (%)"])
            
            # Show only humidity prediction
            hum_pred_df = pred_df[["Humidity (%)"]]
            st.subheader("Humidity Prediction")
            st.line_chart(hum_pred_df)
        
        with tab4:
            st.subheader("Air Quality Over Time")
            st.line_chart(df.set_index("Time")["Air Quality (PPM)"])
            
            # Show only air quality prediction
            aq_pred_df = pred_df[["Air Quality (PPM)"]]
            st.subheader("Air Quality Prediction")
            st.line_chart(aq_pred_df)
    else:
        # Not enough data for prediction, just show historical data
        st.subheader("Historical Data")
        st.line_chart(df.set_index("Time")[["Temperature (°C)", "Humidity (%)", "Air Quality (PPM)"]])
        st.info("Collecting more data for predictions...")

    # Air Quality Interpretation
    st.subheader("Air Quality Analysis")
    st.write(air_quality_message)
    
    # Overall Assessment
    st.subheader("Overall Environmental Assessment")
    overall_message = aq_utils.get_overall_assessment(
        st.session_state.temperatures[-1],
        st.session_state.humidities[-1],
        st.session_state.air_qualities[-1]
    )
    st.write(overall_message)

    # Raw data in expandable section
    with st.expander("View Raw Data"):
        st.dataframe(df)

# Set up automatic refresh - the page will rerun after the specified frequency
time.sleep(1)  # Short pause to prevent excessive CPU usage
st.rerun()
