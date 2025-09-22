import panel as pn
import pandas as pd
import sqlalchemy
import os

pn.extension("tabulator", sizing_mode="stretch_width")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/sensordb")
engine = sqlalchemy.create_engine(DATABASE_URL)

def fetch_data():
    query = "SELECT * FROM sensors ORDER BY id DESC LIMIT 100"
    df = pd.read_sql(query, engine)
    return df

def view():
    df = fetch_data()
    table = pn.widgets.Tabulator(df, height=400, pagination="remote", page_size=20)
    plot = df.hvplot.line(x="id", y="value", title="Sensor Values") if not df.empty else pn.pane.Markdown("⚠️ No data yet")

    return pn.Column(
        "# 📊 Sensor Dashboard",
        "Live sensor readings from Postgres",
        table,
        plot,
    )

pn.template.FastListTemplate(
    title="Sensor Dashboard",
    main=[view],
).servable()
