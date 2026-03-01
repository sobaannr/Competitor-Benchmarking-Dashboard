from flask import Flask, render_template, request
import pandas as pd
import plotly.graph_objects as go
import plotly
import json

app = Flask(__name__)

df      = pd.read_csv("competitor_data.csv")
summary = pd.read_csv("company_summary.csv")
df.columns      = df.columns.str.strip()
summary.columns = summary.columns.str.strip()

ACCENT_PALETTE = ["#00e5a0", "#4d7cff", "#f5c542", "#ff6b6b", "#a78bfa", "#fb923c"]

AXIS_STYLE = dict(
    gridcolor="rgba(255,255,255,0.07)",
    zerolinecolor="rgba(255,255,255,0.12)",
    tickfont=dict(color="#8a9bbf", size=11),
    title_font=dict(color="#8a9bbf", size=12),
    linecolor="rgba(255,255,255,0.1)",
)

def base_layout(title_text):
    return dict(
        paper_bgcolor="#0f1520",
        plot_bgcolor="#0f1520",
        font=dict(family="DM Sans, sans-serif", color="#8a9bbf", size=12),
        margin=dict(t=60, r=30, b=60, l=70),
        title=dict(text=title_text, font=dict(color="#e8edf5", size=14), x=0.0, xanchor="left"),
        legend=dict(
            bgcolor="rgba(255,255,255,0.05)",
            bordercolor="rgba(255,255,255,0.1)",
            borderwidth=1,
            font=dict(color="#e8edf5", size=11),
        ),
        xaxis=dict(**AXIS_STYLE),
        yaxis=dict(**AXIS_STYLE),
    )


@app.route("/", methods=["GET", "POST"])
def dashboard():
    selected_company = request.form.get("company")

    scatter_df = summary.dropna(subset=["avg_price", "avg_features"]).copy()

    v = scatter_df["avg_value"]
    vrange = v.max() - v.min()
    scatter_df["bubble_size"] = ((v - v.min()) / (vrange if vrange > 0 else 1)) * 40 + 20

    scatter_traces = []
    for i, row in scatter_df.iterrows():
        color = ACCENT_PALETTE[list(scatter_df.index).index(i) % len(ACCENT_PALETTE)]
        scatter_traces.append(go.Scatter(
            x=[row["avg_price"]],
            y=[row["avg_features"]],
            mode="markers+text",
            name=row["company"],
            text=[row["company"]],
            textposition="top center",
            textfont=dict(color="#e8edf5", size=12),
            marker=dict(
                size=row["bubble_size"],
                color=color,
                opacity=0.9,
                line=dict(width=2, color="rgba(255,255,255,0.2)"),
            ),
        ))

    layout_market = base_layout("Market Position Map")
    layout_market["xaxis"]["title"] = "Avg. Price ($)"
    layout_market["yaxis"]["title"] = "Avg. Features"
    layout_market["showlegend"] = True

    fig_market_json = json.dumps(
        {"data": [t.to_plotly_json() for t in scatter_traces], "layout": layout_market},
        cls=plotly.utils.PlotlyJSONEncoder
    )

    fig_pricing_json = None
    table_data = None

    if selected_company:
        filtered = (
            df[df["company"] == selected_company]
            .dropna(subset=["price_numeric"])
            .sort_values("price_numeric")
            .copy()
        )

        tier_list   = filtered["tier"].tolist()
        plan_list   = filtered["plan"].tolist()
        price_list  = filtered["price_numeric"].tolist()
        unique_tiers = list(dict.fromkeys(tier_list))  

        bar_traces = []
        for i, tier in enumerate(unique_tiers):
            mask   = filtered["tier"] == tier
            color  = ACCENT_PALETTE[i % len(ACCENT_PALETTE)]
            subset = filtered[mask]
            bar_traces.append(go.Bar(
                name=tier,
                x=subset["plan"].tolist(),
                y=subset["price_numeric"].tolist(),
                text=[f"${v:,.0f}" for v in subset["price_numeric"].tolist()],
                textposition="auto",        
                textfont=dict(color="#080c12", size=12, family="DM Sans, sans-serif"),
                marker=dict(
                    color=color,
                    opacity=1.0,             
                    line=dict(width=0),
                ),
            ))

        max_price = filtered["price_numeric"].max()
        layout_pricing = base_layout(f"{selected_company} — Pricing Breakdown")
        layout_pricing["xaxis"]["title"] = "Plan"
        layout_pricing["yaxis"]["title"] = "Price / mo ($)"
        layout_pricing["yaxis"]["range"]       = [0, max_price * 1.35]
        layout_pricing["yaxis"]["tickprefix"]  = "$"
        layout_pricing["bargap"]   = 0.4
        layout_pricing["bargroupgap"] = 0.1

        fig_pricing_json = json.dumps(
            {"data": [t.to_plotly_json() for t in bar_traces], "layout": layout_pricing},
            cls=plotly.utils.PlotlyJSONEncoder
        )
        table_data = filtered.to_dict(orient="records")

    companies = sorted(df["company"].unique())

    return render_template(
        "index.html",
        companies=companies,
        market_chart=fig_market_json,
        pricing_chart=fig_pricing_json,
        table_data=table_data,
        selected_company=selected_company,
    )


if __name__ == "__main__":
    app.run(debug=True)