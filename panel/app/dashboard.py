import panel as pn
import pandas as pd
import requests
import hvplot.pandas
import os
import json
from datetime import datetime, timedelta

pn.extension("tabulator", sizing_mode="stretch_width")

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")  # Use API instead of direct SQL

# Authentication state using Panel's session state
def get_auth_token():
    """Get auth token from session state"""
    return pn.state.cache.get('auth_token', None)

def set_auth_token(token):
    """Set auth token in session state"""
    pn.state.cache['auth_token'] = token

def is_authenticated():
    """Check if user is authenticated"""
    return get_auth_token() is not None

def login(username, password):
    """Login and get JWT token"""
    try:
        print(f"🔍 Attempting login to {FASTAPI_URL}/login with username: {username}")
        response = requests.post(
            f"{FASTAPI_URL}/login",
            headers={"Content-Type": "application/json"},
            json={"username": username, "password": password}
        )
        print(f"🔍 Login response status: {response.status_code}")
        print(f"🔍 Login response text: {response.text}")
        if response.status_code == 200:
            data = response.json()
            return data["access_token"]
        else:
            return None
    except Exception as e:
        print(f"⚠️ Login error: {e}")
        return None

def download_csv(start_date=None, end_date=None):
    """Download CSV with authentication"""
    if not is_authenticated():
        return "⚠️ Please login first"

    try:
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        url = f"{FASTAPI_URL}/download/csv"
        headers = {"Authorization": f"Bearer {get_auth_token()}"}

        print(f"🔍 CSV Download - URL: {url}")
        print(f"🔍 CSV Download - Params: {params}")
        print(f"🔍 CSV Download - Headers: {headers}")

        response = requests.get(url, headers=headers, params=params)

        print(f"🔍 CSV Download - Response status: {response.status_code}")
        print(f"🔍 CSV Download - Response headers: {dict(response.headers)}")

        if response.status_code == 200:
            content = response.content.decode('utf-8')
            print(f"🔍 CSV Download - Content length: {len(content)} characters")
            return content
        elif response.status_code == 401:
            return "⚠️ Authentication failed. Please login again."
        else:
            error_detail = response.text if response.text else "Unknown error"
            return f"⚠️ Download failed (Status {response.status_code}): {error_detail}"
    except Exception as e:
        print(f"⚠️ CSV Download exception: {e}")
        return f"⚠️ Download error: {e}"

def fetch_data(limit=50, hours=None, start_date=None, end_date=None):
    try:
        params = {}

        if hours:
            # Convert hours to a limit based on expected data frequency
            # Assuming ~4 readings per hour as rough estimate
            estimated_limit = int(hours * 4)
            params["limit"] = max(limit, estimated_limit)
        else:
            params["limit"] = limit

        url = f"{FASTAPI_URL}/data"
        data = requests.get(url, params=params).json()
        df = pd.DataFrame(data)

        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Filter by time range if specified
            if hours:
                cutoff_time = datetime.now() - timedelta(hours=hours)
                df = df[df['timestamp'] >= cutoff_time]
            elif start_date and end_date:
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                df = df[(df['timestamp'] >= start_dt) & (df['timestamp'] <= end_dt)]

            # Data already comes sorted newest first from API
            # Keep only essential columns for display to reduce memory
            display_columns = ['id', 'timestamp', 'oxygen_concentrator_id', 'temperature',
                             'humidity', 'system_in_use', 'oxygen_level', 'vibration_frequency']
            df = df[display_columns]
        return df
    except Exception as e:
        print(f"⚠️ Error fetching data: {e}")
        return pd.DataFrame()

def fetch_latest():
    try:
        url = f"{FASTAPI_URL}/latest"
        response = requests.get(url)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"⚠️ Error fetching latest: {e}")
        return None

def fetch_stats():
    try:
        url = f"{FASTAPI_URL}/stats"
        response = requests.get(url)
        return response.json() if response.status_code == 200 else {}
    except Exception as e:
        print(f"⚠️ Error fetching stats: {e}")
        return {}

def fetch_timeline(hours=24):
    try:
        url = f"{FASTAPI_URL}/timeline?hours={hours}"
        response = requests.get(url)
        return response.json() if response.status_code == 200 else {}
    except Exception as e:
        print(f"⚠️ Error fetching timeline: {e}")
        return {}

def create_login_screen():
    """Create login screen"""
    username_input = pn.widgets.TextInput(name="Username", placeholder="Enter username")
    password_input = pn.widgets.PasswordInput(name="Password", placeholder="Enter password")
    login_button = pn.widgets.Button(name="Login", button_type="primary")
    login_status = pn.pane.Markdown("", sizing_mode="stretch_width")

    def handle_login(event):
        print(f"🔍 Login button clicked! Username: '{username_input.value}', Password length: {len(password_input.value)}")
        login_status.object = "⏳ Attempting login..."
        token = login(username_input.value, password_input.value)
        print(f"🔍 Received token: {token[:20] + '...' if token else None}")
        if token:
            set_auth_token(token)
            login_status.object = "✅ Login successful! Redirecting..."
            print("✅ Login successful! Token stored in session cache.")
            # Auto-reload the page to show the dashboard
            pn.state.location.reload = True
        else:
            login_status.object = "❌ Invalid credentials. Please try again."

    login_button.on_click(handle_login)

    return pn.Column(
        "# 🔐 Oxygen Concentrator Dashboard - Login",
        pn.Spacer(height=50),
        pn.Row(
            pn.Spacer(width=100),
            pn.Column(
                "## Please Login",
                username_input,
                password_input,
                login_button,
                login_status,
                width=300,
                styles={"border": "1px solid #ddd", "padding": "20px", "border-radius": "5px"}
            ),
            pn.Spacer(width=100),
            sizing_mode="stretch_width"
        ),
        pn.Spacer(height=100),
        sizing_mode="stretch_width"
    )

def view():
    # Check if authenticated
    if not is_authenticated():
        return create_login_screen()

    df = fetch_data()
    latest = fetch_latest()
    stats = fetch_stats()

    # Current value display
    latest_value_text = "⚠️ No data available"
    if latest:
        latest_value_text = f"**Latest Value:** {latest['value']} (ID: {latest['oxygen_concentrator_id']}) at {latest['timestamp'][:19] if latest['timestamp'] else 'Unknown time'}"

    latest_display = pn.pane.Markdown(latest_value_text, sizing_mode="stretch_width")

    # Operational statistics display
    stats_text = "## 📈 Operational Statistics\n"
    if stats:
        for period, data in stats.items():
            if period in ['24h', '7d', '30d']:
                stats_text += f"**{period.upper()}:** {data['operational_hours']}h operational  "
    else:
        stats_text += "⚠️ Statistics not available"

    stats_display = pn.pane.Markdown(stats_text, sizing_mode="stretch_width")

    # Create reactive components that will be updated
    table = pn.widgets.Tabulator(
        df,
        height=400,
        pagination="remote",
        page_size=15,
        frozen_columns=[],
        show_index=False
    )

    def create_plots(df):
        plots = {}
        if not df.empty and 'timestamp' in df.columns:
            # Ensure timestamp is properly formatted and sorted
            df = df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')

            # Filter out any rows with invalid timestamps
            df = df.dropna(subset=['timestamp'])

            if df.empty:
                return plots

            # Temperature plot
            if 'temperature' in df.columns:
                temp_df = df.dropna(subset=['temperature'])
                if not temp_df.empty and len(temp_df) > 0:
                    # Ensure temperature is numeric
                    temp_df['temperature'] = pd.to_numeric(temp_df['temperature'], errors='coerce')
                    temp_df = temp_df.dropna(subset=['temperature'])
                    if not temp_df.empty:
                        plots['Temperature'] = temp_df.hvplot.line(
                            x="timestamp", y="temperature",
                            title="Temperature Over Time (°C)",
                            ylabel="Temperature (°C)"
                        )

            # Humidity plot
            if 'humidity' in df.columns:
                humid_df = df.dropna(subset=['humidity'])
                if not humid_df.empty and len(humid_df) > 0:
                    # Ensure humidity is numeric
                    humid_df['humidity'] = pd.to_numeric(humid_df['humidity'], errors='coerce')
                    humid_df = humid_df.dropna(subset=['humidity'])
                    if not humid_df.empty:
                        plots['Humidity'] = humid_df.hvplot.line(
                            x="timestamp", y="humidity",
                            title="Humidity Over Time (%)",
                            ylabel="Humidity (%)"
                        )

            # Oxygen level plot
            if 'oxygen_level' in df.columns:
                oxygen_df = df.dropna(subset=['oxygen_level'])
                if not oxygen_df.empty and len(oxygen_df) > 0:
                    # Ensure oxygen_level is numeric
                    oxygen_df['oxygen_level'] = pd.to_numeric(oxygen_df['oxygen_level'], errors='coerce')
                    oxygen_df = oxygen_df.dropna(subset=['oxygen_level'])
                    if not oxygen_df.empty:
                        plots['Oxygen Level'] = oxygen_df.hvplot.line(
                            x="timestamp", y="oxygen_level",
                            title="Oxygen Level Over Time",
                            ylabel="Oxygen Level"
                        )

            # Vibration frequency plot
            if 'vibration_frequency' in df.columns:
                vibration_df = df.dropna(subset=['vibration_frequency'])
                if not vibration_df.empty and len(vibration_df) > 0:
                    # Ensure vibration_frequency is numeric
                    vibration_df['vibration_frequency'] = pd.to_numeric(vibration_df['vibration_frequency'], errors='coerce')
                    vibration_df = vibration_df.dropna(subset=['vibration_frequency'])
                    if not vibration_df.empty:
                        plots['Vibration'] = vibration_df.hvplot.line(
                            x="timestamp", y="vibration_frequency",
                            title="Vibration Frequency Over Time (Hz)",
                            ylabel="Frequency (Hz)"
                        )

            # System usage plot
            if 'system_in_use' in df.columns:
                usage_df = df.dropna(subset=['system_in_use'])
                if not usage_df.empty and len(usage_df) > 0:
                    # Convert boolean/string to numeric safely
                    try:
                        usage_df['system_in_use_numeric'] = usage_df['system_in_use'].astype(int)
                        plots['System Usage'] = usage_df.hvplot.step(
                            x="timestamp", y="system_in_use_numeric",
                            title="System Usage Over Time",
                            ylabel="In Use (1=Yes, 0=No)"
                        )
                    except (ValueError, TypeError):
                        # Skip this plot if data can't be converted
                        pass

        return plots

    initial_plots = create_plots(df)

    # Create tabbed plot interface
    if initial_plots:
        plot_tabs = []
        plot_panes = {}
        for plot_name, plot_obj in initial_plots.items():
            plot_pane = pn.pane.HoloViews(plot_obj)
            plot_panes[plot_name] = plot_pane
            plot_tabs.append((plot_name, plot_pane))

        plots_container = pn.Tabs(*plot_tabs, tabs_location="above")
    else:
        plots_container = pn.pane.Markdown("⚠️ No data available for plotting")
        plot_panes = {}

    # Timeframe selectors for graphs
    timeframe_select = pn.widgets.Select(
        name="Timeframe",
        options={
            "Last 24 Hours": 24,
            "Last 3 Days": 72,
            "Last Week": 168,
            "Last Month": 720,
            "Custom Range": "custom"
        },
        value=24
    )

    start_date_picker = pn.widgets.DatetimePicker(
        name="Start Date",
        value=datetime.now() - timedelta(days=1),
        visible=False
    )

    end_date_picker = pn.widgets.DatetimePicker(
        name="End Date",
        value=datetime.now(),
        visible=False
    )

    refresh_button = pn.widgets.Button(name="🔄 Refresh Graphs", button_type="primary")

    def update_timeframe_visibility(event):
        """Show/hide custom date pickers based on timeframe selection"""
        if event.new == "custom":
            start_date_picker.visible = True
            end_date_picker.visible = True
        else:
            start_date_picker.visible = False
            end_date_picker.visible = False

    def refresh_graphs_with_timeframe(event):
        """Refresh graphs based on selected timeframe"""
        if timeframe_select.value == "custom":
            # Use custom date range
            new_df = fetch_data(
                limit=1000,
                start_date=start_date_picker.value,
                end_date=end_date_picker.value
            )
        else:
            # Use predefined timeframe
            hours = timeframe_select.value
            new_df = fetch_data(hours=hours, limit=1000)

        # Update all plots with new data
        new_plots = create_plots(new_df)
        if new_plots and plot_panes:
            for plot_name, new_plot_obj in new_plots.items():
                if plot_name in plot_panes:
                    plot_panes[plot_name].object = new_plot_obj

        # Also update the table
        table.value = new_df

    # Set up event handlers
    timeframe_select.param.watch(update_timeframe_visibility, 'value')
    refresh_button.on_click(refresh_graphs_with_timeframe)

    # Timeframe controls
    timeframe_controls = pn.Row(
        timeframe_select,
        start_date_picker,
        end_date_picker,
        refresh_button,
        sizing_mode="stretch_width"
    )

    # Usage visualization tab
    def create_usage_plot(hours=24):
        timeline_data = fetch_timeline(hours)

        if not timeline_data or not timeline_data.get('buckets'):
            return pn.pane.Markdown("## 📊 Usage Timeline\n\n⚠️ No timeline data available")

        # Create timeline visualization using panel components
        buckets = timeline_data['buckets']
        bucket_size = timeline_data.get('bucket_size_minutes', 15)

        # Create improved timeline visualization
        blocks = []
        time_labels = []

        for i, bucket in enumerate(buckets):
            # Enhanced color scheme based on operational status and reading count
            if bucket['operational']:
                if bucket['reading_count'] > 2:
                    color = "#2E7D32"  # Dark green for high activity
                else:
                    color = "#4CAF50"  # Medium green for normal activity
            else:
                color = "#E0E0E0"  # Light gray for non-operational

            # Create time label for every 4th bucket (1 hour intervals)
            time_label = ""
            if i % 4 == 0:
                start_time = pd.to_datetime(bucket['start'])
                time_label = start_time.strftime("%H:%M")

            block_html = f"""
            <div style="display: inline-block; width: 16px; height: 40px; background-color: {color};
                        border: none; margin: 0px; vertical-align: top; border-radius: 2px;"
                 title="Time: {bucket['start'][:16]} - Operational: {bucket['operational']} - Readings: {bucket['reading_count']}">
            </div>
            """
            blocks.append(block_html)

            # Create time labels separately for better alignment
            if time_label:
                time_labels.append(f'<div style="display: inline-block; width: 64px; font-size: 10px; text-align: left; margin-right: 0px; color: #666;">{time_label}</div>')
            else:
                time_labels.append('<div style="display: inline-block; width: 16px;"></div>')

        # Calculate operational statistics for the period
        total_buckets = len(buckets)
        operational_buckets = sum(1 for bucket in buckets if bucket['operational'])
        operational_percentage = (operational_buckets / total_buckets * 100) if total_buckets > 0 else 0

        timeline_html = f"""
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
            <h3 style="color: #333; margin-bottom: 20px;">📊 Oxygen Concentrator Usage Timeline - Last {hours} Hours</h3>

            <!-- Summary Stats -->
            <div style="background: #e8f5e8; border: 1px solid #c3e6cb; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: #155724; font-size: 16px;">System Operational: {operational_percentage:.1f}% of the time</strong>
                        <p style="color: #155724; margin: 5px 0 0 0; font-size: 14px;">
                            {operational_buckets} out of {total_buckets} time periods ({bucket_size}-minute intervals)
                        </p>
                    </div>
                    <div style="text-align: right;">
                        <span style="color: #155724; font-size: 24px; font-weight: bold;">{operational_percentage:.0f}%</span>
                    </div>
                </div>
            </div>

            <div style="margin-bottom: 15px;">
                <p style="color: #666; margin-bottom: 10px; font-size: 14px;">
                    <strong>How to read this timeline:</strong> Each colored block represents {bucket_size} minutes.
                    The oxygen concentrator is considered "operational" when it sends sensor data during that time period.
                </p>
                <p style="color: #666; margin-bottom: 15px; font-size: 14px;">
                    <strong>Time flows from left to right.</strong> Hover over any block to see detailed information about that time period.
                </p>
            </div>

            <!-- Time labels -->
            <div style="margin-bottom: 5px; height: 15px;">
                {''.join(time_labels)}
            </div>

            <!-- Timeline blocks -->
            <div style="margin: 10px 0; padding: 15px; background: #fafafa; border-radius: 8px; border: 1px solid #e0e0e0;">
                {''.join(blocks)}
            </div>

            <!-- Enhanced legend with detailed explanations -->
            <div style="margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
                <h4 style="color: #333; margin-bottom: 10px;">Legend & Explanation:</h4>
                <div style="display: grid; gap: 10px;">
                    <div style="display: flex; align-items: center;">
                        <span style="background: #2E7D32; width: 20px; height: 20px; display: inline-block; border-radius: 3px; margin-right: 10px;"></span>
                        <span style="color: #333;"><strong>High Activity:</strong> Multiple sensor readings received (3+ per {bucket_size} minutes) - system actively working</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <span style="background: #4CAF50; width: 20px; height: 20px; display: inline-block; border-radius: 3px; margin-right: 10px;"></span>
                        <span style="color: #333;"><strong>Normal Activity:</strong> Regular sensor readings received (1-2 per {bucket_size} minutes) - system operational</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <span style="background: #E0E0E0; width: 20px; height: 20px; display: inline-block; border-radius: 3px; margin-right: 10px;"></span>
                        <span style="color: #333;"><strong>Not Operational:</strong> No sensor data received - system may be off, disconnected, or having issues</span>
                    </div>
                </div>
                <div style="margin-top: 15px; padding: 10px; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px;">
                    <small style="color: #856404;">
                        <strong>Note:</strong> This visualization helps identify usage patterns, maintenance windows, and potential system issues.
                        Consistent gaps may indicate scheduled maintenance or connectivity problems.
                    </small>
                </div>
            </div>
        </div>
        """

        return pn.pane.HTML(timeline_html, sizing_mode="stretch_width")

    # Time period selector for usage visualization
    period_selector = pn.widgets.Select(name="Time Period", options={"Last 24 Hours": 24, "Last 3 Days": 72, "Last Week": 168}, value=24)

    def update_usage_plot(event=None):
        hours = period_selector.value
        return create_usage_plot(hours)

    initial_usage_plot = create_usage_plot(24)
    if hasattr(initial_usage_plot, 'object'):
        usage_plot = initial_usage_plot
    else:
        usage_plot = initial_usage_plot

    def usage_period_change(event):
        new_usage_plot = create_usage_plot(event.new)
        if hasattr(new_usage_plot, 'object') and hasattr(usage_plot, 'object'):
            usage_plot.object = new_usage_plot.object
        else:
            # Handle different pane types
            usage_plot.object = new_usage_plot

    period_selector.param.watch(usage_period_change, 'value')

    def update_data():
        new_df = fetch_data()
        new_latest = fetch_latest()
        new_stats = fetch_stats()

        # Update table and plots
        table.value = new_df
        new_plots = create_plots(new_df)

        # Update each plot pane in the tabs
        if new_plots and plot_panes:
            for plot_name, new_plot_obj in new_plots.items():
                if plot_name in plot_panes:
                    plot_panes[plot_name].object = new_plot_obj
        elif not new_plots:
            print("⚠️ No data available for plots")

        # Update latest value
        if new_latest:
            latest_text = f"**Latest Value:** {new_latest['value']} (ID: {new_latest['oxygen_concentrator_id']}) at {new_latest['timestamp'][:19] if new_latest['timestamp'] else 'Unknown time'}"
        else:
            latest_text = "⚠️ No data available"
        latest_display.object = latest_text

        # Update stats
        updated_stats_text = "## 📈 Operational Statistics\n"
        if new_stats:
            for period, data in new_stats.items():
                if period in ['24h', '7d', '30d']:
                    updated_stats_text += f"**{period.upper()}:** {data['operational_hours']}h operational  "
        else:
            updated_stats_text += "⚠️ Statistics not available"
        stats_display.object = updated_stats_text

    # Update every 5 seconds for better performance
    pn.state.add_periodic_callback(update_data, 5000)

    # CSV Download section
    csv_download_button = pn.widgets.Button(name="📥 Download CSV", button_type="primary")
    start_date_input = pn.widgets.DatePicker(name="Start Date", value=datetime.now().date() - timedelta(days=7))
    end_date_input = pn.widgets.DatePicker(name="End Date", value=datetime.now().date())
    download_status = pn.pane.HTML("", sizing_mode="stretch_width")

    def handle_csv_download(event):
        start_date_str = start_date_input.value.isoformat() + "T00:00:00" if start_date_input.value else None
        end_date_str = end_date_input.value.isoformat() + "T23:59:59" if end_date_input.value else None

        download_status.object = "⏳ Downloading CSV..."
        csv_content = download_csv(start_date_str, end_date_str)

        if csv_content.startswith("⚠️"):
            download_status.object = csv_content
        else:
            # Create a data URL for direct download
            import base64
            csv_base64 = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
            filename = f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            download_link_html = f"""
            <div style="margin: 10px 0;">
                <a href="data:text/csv;base64,{csv_base64}"
                   download="{filename}"
                   style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;"
                   id="csv_download_link_main">
                    📥 Download CSV File
                </a>
                <p style="margin-top: 10px; color: #666; font-size: 12px;">
                    Click the button above to download the CSV file directly.
                </p>
                <script>
                    // Auto-trigger download
                    setTimeout(function() {{
                        document.getElementById('csv_download_link_main').click();
                    }}, 100);
                </script>
            </div>
            """

            # Update the status with HTML content
            success_html = f"""
            <div style="background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <strong>✅ CSV ready for download!</strong>
                {download_link_html}
            </div>
            """
            download_status.object = success_html

    csv_download_button.on_click(handle_csv_download)

    csv_section = pn.Column(
        "### 📥 Export Data",
        pn.Row(start_date_input, end_date_input, csv_download_button),
        download_status,
    )

    # Create main content without tabs
    main_content = pn.Column(
        latest_display,
        stats_display,
        csv_section,
        "### 📋 Recent Data",
        table,
        "### 📈 Sensor Plots",
        "#### Timeframe Selection",
        timeframe_controls,
        plots_container,
    )

    # Logout button
    logout_button = pn.widgets.Button(name="🚪 Logout", button_type="primary")

    def handle_logout(event):
        set_auth_token(None)
        pn.state.location.reload = True

    logout_button.on_click(handle_logout)

    header = pn.Row(
        "# 📊 Oxygen Concentrator Dashboard",
        pn.Spacer(),
        logout_button,
        sizing_mode="stretch_width"
    )

    return pn.Column(
        header,
        "Live monitoring and analytics (updates every 5s)",
        main_content,
    )

# Create a reactive dashboard that updates based on authentication state
def create_dashboard():
    """Create reactive dashboard"""
    # Main container that will hold either login or dashboard
    main_container = pn.Column(sizing_mode="stretch_width")

    def update_content():
        """Update the main content based on authentication state"""
        if is_authenticated():
            # Show the dashboard
            main_container.objects = [create_main_dashboard()]
        else:
            # Show the login screen
            main_container.objects = [create_login_screen()]

    # Initial content
    update_content()

    # Return the reactive container
    return main_container

def create_main_dashboard():
    """Create the main dashboard content (previously the view function)"""
    df = fetch_data()
    latest = fetch_latest()
    stats = fetch_stats()

    # Current value display
    latest_value_text = "⚠️ No data available"
    if latest:
        latest_value_text = f"**Latest Value:** {latest['value']} (ID: {latest['oxygen_concentrator_id']}) at {latest['timestamp'][:19] if latest['timestamp'] else 'Unknown time'}"

    latest_display = pn.pane.Markdown(latest_value_text, sizing_mode="stretch_width")

    # Operational statistics display
    stats_text = "## 📈 Operational Statistics\\n"
    if stats:
        for period, data in stats.items():
            if period in ['24h', '7d', '30d']:
                stats_text += f"**{period.upper()}:** {data['operational_hours']}h operational  "
    else:
        stats_text += "⚠️ Statistics not available"

    stats_display = pn.pane.Markdown(stats_text, sizing_mode="stretch_width")

    # Create reactive components that will be updated
    table = pn.widgets.Tabulator(
        df,
        height=400,
        pagination="remote",
        page_size=15,
        frozen_columns=[],
        show_index=False
    )

    def create_plots(df):
        plots = {}
        if not df.empty and 'timestamp' in df.columns:
            # Ensure timestamp is properly formatted and sorted
            df = df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')

            # Filter out any rows with invalid timestamps
            df = df.dropna(subset=['timestamp'])

            if df.empty:
                return plots

            # Temperature plot
            if 'temperature' in df.columns:
                temp_df = df.dropna(subset=['temperature'])
                if not temp_df.empty and len(temp_df) > 0:
                    # Ensure temperature is numeric
                    temp_df['temperature'] = pd.to_numeric(temp_df['temperature'], errors='coerce')
                    temp_df = temp_df.dropna(subset=['temperature'])
                    if not temp_df.empty:
                        plots['Temperature'] = temp_df.hvplot.line(
                            x="timestamp", y="temperature",
                            title="Temperature Over Time (°C)",
                            ylabel="Temperature (°C)"
                        )

            # Humidity plot
            if 'humidity' in df.columns:
                humid_df = df.dropna(subset=['humidity'])
                if not humid_df.empty and len(humid_df) > 0:
                    # Ensure humidity is numeric
                    humid_df['humidity'] = pd.to_numeric(humid_df['humidity'], errors='coerce')
                    humid_df = humid_df.dropna(subset=['humidity'])
                    if not humid_df.empty:
                        plots['Humidity'] = humid_df.hvplot.line(
                            x="timestamp", y="humidity",
                            title="Humidity Over Time (%)",
                            ylabel="Humidity (%)"
                        )

            # Oxygen level plot
            if 'oxygen_level' in df.columns:
                oxygen_df = df.dropna(subset=['oxygen_level'])
                if not oxygen_df.empty and len(oxygen_df) > 0:
                    # Ensure oxygen_level is numeric
                    oxygen_df['oxygen_level'] = pd.to_numeric(oxygen_df['oxygen_level'], errors='coerce')
                    oxygen_df = oxygen_df.dropna(subset=['oxygen_level'])
                    if not oxygen_df.empty:
                        plots['Oxygen Level'] = oxygen_df.hvplot.line(
                            x="timestamp", y="oxygen_level",
                            title="Oxygen Level Over Time",
                            ylabel="Oxygen Level"
                        )

            # Vibration frequency plot
            if 'vibration_frequency' in df.columns:
                vibration_df = df.dropna(subset=['vibration_frequency'])
                if not vibration_df.empty and len(vibration_df) > 0:
                    # Ensure vibration_frequency is numeric
                    vibration_df['vibration_frequency'] = pd.to_numeric(vibration_df['vibration_frequency'], errors='coerce')
                    vibration_df = vibration_df.dropna(subset=['vibration_frequency'])
                    if not vibration_df.empty:
                        plots['Vibration'] = vibration_df.hvplot.line(
                            x="timestamp", y="vibration_frequency",
                            title="Vibration Frequency Over Time (Hz)",
                            ylabel="Frequency (Hz)"
                        )

            # System usage plot
            if 'system_in_use' in df.columns:
                usage_df = df.dropna(subset=['system_in_use'])
                if not usage_df.empty and len(usage_df) > 0:
                    # Convert boolean/string to numeric safely
                    try:
                        usage_df['system_in_use_numeric'] = usage_df['system_in_use'].astype(int)
                        plots['System Usage'] = usage_df.hvplot.step(
                            x="timestamp", y="system_in_use_numeric",
                            title="System Usage Over Time",
                            ylabel="In Use (1=Yes, 0=No)"
                        )
                    except (ValueError, TypeError):
                        # Skip this plot if data can't be converted
                        pass

        return plots

    initial_plots = create_plots(df)

    # Create tabbed plot interface
    if initial_plots:
        plot_tabs = []
        plot_panes = {}
        for plot_name, plot_obj in initial_plots.items():
            plot_pane = pn.pane.HoloViews(plot_obj)
            plot_panes[plot_name] = plot_pane
            plot_tabs.append((plot_name, plot_pane))

        plots_container = pn.Tabs(*plot_tabs, tabs_location="above")
    else:
        plots_container = pn.pane.Markdown("⚠️ No data available for plotting")
        plot_panes = {}

    # Timeframe selectors for graphs
    timeframe_select = pn.widgets.Select(
        name="Timeframe",
        options={
            "Last 24 Hours": 24,
            "Last 3 Days": 72,
            "Last Week": 168,
            "Last Month": 720,
            "Custom Range": "custom"
        },
        value=24
    )

    start_date_picker = pn.widgets.DatetimePicker(
        name="Start Date",
        value=datetime.now() - timedelta(days=1),
        visible=False
    )

    end_date_picker = pn.widgets.DatetimePicker(
        name="End Date",
        value=datetime.now(),
        visible=False
    )

    refresh_button = pn.widgets.Button(name="🔄 Refresh Graphs", button_type="primary")

    def update_timeframe_visibility(event):
        """Show/hide custom date pickers based on timeframe selection"""
        if event.new == "custom":
            start_date_picker.visible = True
            end_date_picker.visible = True
        else:
            start_date_picker.visible = False
            end_date_picker.visible = False

    def refresh_graphs_with_timeframe(event):
        """Refresh graphs based on selected timeframe"""
        if timeframe_select.value == "custom":
            # Use custom date range
            new_df = fetch_data(
                limit=1000,
                start_date=start_date_picker.value,
                end_date=end_date_picker.value
            )
        else:
            # Use predefined timeframe
            hours = timeframe_select.value
            new_df = fetch_data(hours=hours, limit=1000)

        # Update all plots with new data
        new_plots = create_plots(new_df)
        if new_plots and plot_panes:
            for plot_name, new_plot_obj in new_plots.items():
                if plot_name in plot_panes:
                    plot_panes[plot_name].object = new_plot_obj

        # Also update the table
        table.value = new_df

    # Set up event handlers
    timeframe_select.param.watch(update_timeframe_visibility, 'value')
    refresh_button.on_click(refresh_graphs_with_timeframe)

    # Timeframe controls
    timeframe_controls = pn.Row(
        timeframe_select,
        start_date_picker,
        end_date_picker,
        refresh_button,
        sizing_mode="stretch_width"
    )

    # Usage visualization tab
    def create_usage_plot(hours=24):
        timeline_data = fetch_timeline(hours)

        if not timeline_data or not timeline_data.get('buckets'):
            return pn.pane.Markdown("## 📊 Usage Timeline\\n\\n⚠️ No timeline data available")

        # Create improved timeline visualization
        buckets = timeline_data['buckets']
        bucket_size = timeline_data.get('bucket_size_minutes', 15)

        # Create improved timeline visualization
        blocks = []
        time_labels = []

        for i, bucket in enumerate(buckets):
            # Enhanced color scheme based on operational status and reading count
            if bucket['operational']:
                if bucket['reading_count'] > 2:
                    color = "#2E7D32"  # Dark green for high activity
                else:
                    color = "#4CAF50"  # Medium green for normal activity
            else:
                color = "#E0E0E0"  # Light gray for non-operational

            # Create time label for every 4th bucket (1 hour intervals)
            time_label = ""
            if i % 4 == 0:
                start_time = pd.to_datetime(bucket['start'])
                time_label = start_time.strftime("%H:%M")

            block_html = f"""
            <div style="display: inline-block; width: 16px; height: 40px; background-color: {color};
                        border: none; margin: 0px; vertical-align: top; border-radius: 2px;"
                 title="Time: {bucket['start'][:16]} - Operational: {bucket['operational']} - Readings: {bucket['reading_count']}">
            </div>
            """
            blocks.append(block_html)

            # Create time labels separately for better alignment
            if time_label:
                time_labels.append(f'<div style="display: inline-block; width: 64px; font-size: 10px; text-align: left; margin-right: 0px; color: #666;">{time_label}</div>')
            else:
                time_labels.append('<div style="display: inline-block; width: 16px;"></div>')

        # Calculate operational statistics for the period
        total_buckets = len(buckets)
        operational_buckets = sum(1 for bucket in buckets if bucket['operational'])
        operational_percentage = (operational_buckets / total_buckets * 100) if total_buckets > 0 else 0

        timeline_html = f"""
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
            <h3 style="color: #333; margin-bottom: 20px;">📊 Oxygen Concentrator Usage Timeline - Last {hours} Hours</h3>

            <!-- Summary Stats -->
            <div style="background: #e8f5e8; border: 1px solid #c3e6cb; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: #155724; font-size: 16px;">System Operational: {operational_percentage:.1f}% of the time</strong>
                        <p style="color: #155724; margin: 5px 0 0 0; font-size: 14px;">
                            {operational_buckets} out of {total_buckets} time periods ({bucket_size}-minute intervals)
                        </p>
                    </div>
                    <div style="text-align: right;">
                        <span style="color: #155724; font-size: 24px; font-weight: bold;">{operational_percentage:.0f}%</span>
                    </div>
                </div>
            </div>

            <div style="margin-bottom: 15px;">
                <p style="color: #666; margin-bottom: 10px; font-size: 14px;">
                    <strong>How to read this timeline:</strong> Each colored block represents {bucket_size} minutes.
                    The oxygen concentrator is considered "operational" when it sends sensor data during that time period.
                </p>
                <p style="color: #666; margin-bottom: 15px; font-size: 14px;">
                    <strong>Time flows from left to right.</strong> Hover over any block to see detailed information about that time period.
                </p>
            </div>

            <!-- Time labels -->
            <div style="margin-bottom: 5px; height: 15px;">
                {''.join(time_labels)}
            </div>

            <!-- Timeline blocks -->
            <div style="margin: 10px 0; padding: 15px; background: #fafafa; border-radius: 8px; border: 1px solid #e0e0e0;">
                {''.join(blocks)}
            </div>

            <!-- Enhanced legend with detailed explanations -->
            <div style="margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;">
                <h4 style="color: #333; margin-bottom: 10px;">Legend & Explanation:</h4>
                <div style="display: grid; gap: 10px;">
                    <div style="display: flex; align-items: center;">
                        <span style="background: #2E7D32; width: 20px; height: 20px; display: inline-block; border-radius: 3px; margin-right: 10px;"></span>
                        <span style="color: #333;"><strong>High Activity:</strong> Multiple sensor readings received (3+ per {bucket_size} minutes) - system actively working</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <span style="background: #4CAF50; width: 20px; height: 20px; display: inline-block; border-radius: 3px; margin-right: 10px;"></span>
                        <span style="color: #333;"><strong>Normal Activity:</strong> Regular sensor readings received (1-2 per {bucket_size} minutes) - system operational</span>
                    </div>
                    <div style="display: flex; align-items: center;">
                        <span style="background: #E0E0E0; width: 20px; height: 20px; display: inline-block; border-radius: 3px; margin-right: 10px;"></span>
                        <span style="color: #333;"><strong>Not Operational:</strong> No sensor data received - system may be off, disconnected, or having issues</span>
                    </div>
                </div>
                <div style="margin-top: 15px; padding: 10px; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px;">
                    <small style="color: #856404;">
                        <strong>Note:</strong> This visualization helps identify usage patterns, maintenance windows, and potential system issues.
                        Consistent gaps may indicate scheduled maintenance or connectivity problems.
                    </small>
                </div>
            </div>
        </div>
        """

        return pn.pane.HTML(timeline_html, sizing_mode="stretch_width")

    # Time period selector for usage visualization
    period_selector = pn.widgets.Select(name="Time Period", options={"Last 24 Hours": 24, "Last 3 Days": 72, "Last Week": 168}, value=24)

    initial_usage_plot = create_usage_plot(24)
    if hasattr(initial_usage_plot, 'object'):
        usage_plot = initial_usage_plot
    else:
        usage_plot = initial_usage_plot

    def usage_period_change(event):
        new_usage_plot = create_usage_plot(event.new)
        if hasattr(new_usage_plot, 'object') and hasattr(usage_plot, 'object'):
            usage_plot.object = new_usage_plot.object
        else:
            # Handle different pane types
            usage_plot.object = new_usage_plot

    period_selector.param.watch(usage_period_change, 'value')

    def update_data():
        new_df = fetch_data()
        new_latest = fetch_latest()
        new_stats = fetch_stats()

        # Update table and plots
        table.value = new_df
        new_plots = create_plots(new_df)

        # Update each plot pane in the tabs
        if new_plots and plot_panes:
            for plot_name, new_plot_obj in new_plots.items():
                if plot_name in plot_panes:
                    plot_panes[plot_name].object = new_plot_obj
        elif not new_plots:
            print("⚠️ No data available for plots")

        # Update latest value
        if new_latest:
            latest_text = f"**Latest Value:** {new_latest['value']} (ID: {new_latest['oxygen_concentrator_id']}) at {new_latest['timestamp'][:19] if new_latest['timestamp'] else 'Unknown time'}"
        else:
            latest_text = "⚠️ No data available"
        latest_display.object = latest_text

        # Update stats
        updated_stats_text = "## 📈 Operational Statistics\\n"
        if new_stats:
            for period, data in new_stats.items():
                if period in ['24h', '7d', '30d']:
                    updated_stats_text += f"**{period.upper()}:** {data['operational_hours']}h operational  "
        else:
            updated_stats_text += "⚠️ Statistics not available"
        stats_display.object = updated_stats_text

    # Update every 5 seconds for better performance
    pn.state.add_periodic_callback(update_data, 5000)

    # CSV Download section
    csv_download_button = pn.widgets.Button(name="📥 Download CSV", button_type="primary")
    start_date_input = pn.widgets.DatePicker(name="Start Date", value=datetime.now().date() - timedelta(days=7))
    end_date_input = pn.widgets.DatePicker(name="End Date", value=datetime.now().date())
    download_status = pn.pane.HTML("", sizing_mode="stretch_width")

    def handle_csv_download(event):
        start_date_str = start_date_input.value.isoformat() + "T00:00:00" if start_date_input.value else None
        end_date_str = end_date_input.value.isoformat() + "T23:59:59" if end_date_input.value else None

        download_status.object = "⏳ Downloading CSV..."
        csv_content = download_csv(start_date_str, end_date_str)

        if csv_content.startswith("⚠️"):
            download_status.object = csv_content
        else:
            # Create a data URL for direct download
            import base64
            csv_base64 = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')
            filename = f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            download_link_html = f"""
            <div style="margin: 10px 0;">
                <a href="data:text/csv;base64,{csv_base64}"
                   download="{filename}"
                   style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;"
                   id="csv_download_link">
                    📥 Download CSV File
                </a>
                <p style="margin-top: 10px; color: #666; font-size: 12px;">
                    Click the button above to download the CSV file directly.
                </p>
                <script>
                    // Auto-trigger download
                    setTimeout(function() {{
                        document.getElementById('csv_download_link').click();
                    }}, 100);
                </script>
            </div>
            """

            # Update the status with HTML content
            success_html = f"""
            <div style="background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <strong>✅ CSV ready for download!</strong>
                {download_link_html}
            </div>
            """
            download_status.object = success_html

    csv_download_button.on_click(handle_csv_download)

    csv_section = pn.Column(
        "### 📥 Export Data",
        pn.Row(start_date_input, end_date_input, csv_download_button),
        download_status,
    )

    # Create main content without tabs
    main_content = pn.Column(
        latest_display,
        stats_display,
        csv_section,
        "### 📋 Recent Data",
        table,
        "### 📈 Sensor Plots",
        "#### Timeframe Selection",
        timeframe_controls,
        plots_container,
    )

    # Logout button
    logout_button = pn.widgets.Button(name="🚪 Logout", button_type="primary")

    def handle_logout(event):
        set_auth_token(None)
        # Instead of page reload, update the dashboard content
        main_container = event.obj.parent.parent  # Navigate up to the main container
        main_container.objects = [create_login_screen()]

    logout_button.on_click(handle_logout)

    header = pn.Row(
        "# 📊 Oxygen Concentrator Dashboard",
        pn.Spacer(),
        logout_button,
        sizing_mode="stretch_width"
    )

    return pn.Column(
        header,
        "Live monitoring and analytics (updates every 5s)",
        main_content,
    )

pn.template.FastListTemplate(
    title="Sensor Dashboard",
    main=[create_dashboard],
).servable()
