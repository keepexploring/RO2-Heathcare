import panel as pn
import pandas as pd
import requests
import hvplot.pandas
import os

pn.extension("tabulator", sizing_mode="stretch_width")

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")  # Use API instead of direct SQL

def fetch_data(limit=100):
    try:
        url = f"{FASTAPI_URL}/data?limit={limit}"
        data = requests.get(url).json()
        df = pd.DataFrame(data)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
        return df
    except Exception as e:
        print(f"⚠️ Error fetching data: {e}")
        return pd.DataFrame()

def view():
    def update_data():
        df = fetch_data()
        table.value = df
        # Just update the data source, not recreate the plot
        if not df.empty:
            plot.param.trigger('object')
        return df

    df = fetch_data()
    table = pn.widgets.Tabulator(df, height=400, pagination="remote", page_size=20) if not df.empty else pn.widgets.Tabulator(pd.DataFrame(), height=400)

    # Create a bound plot that updates with new data
    @pn.depends(table.param.value)
    def create_plot(*args):
        current_df = table.value if hasattr(table.value, 'empty') else df
        if not current_df.empty:
            return current_df.hvplot.line(x="timestamp", y="value", title="Sensor Values")
        else:
            return pn.pane.Markdown("⚠️ No data yet")

    plot = pn.pane.HoloViews(create_plot)

    # Update every 2 seconds
    pn.state.add_periodic_callback(update_data, 2000)

    return pn.Column(
        "# 📊 Sensor Dashboard",
        "Live sensor readings from FastAPI (updates every 2s)",
        table,
        plot,
    )

pn.template.FastListTemplate(
    title="Sensor Dashboard",
    main=[view],
).servable()
