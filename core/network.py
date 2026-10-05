"""Knowledge graph: herbs as nodes, strong pairs as edges (plotly figure)."""

from __future__ import annotations

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

GREEN_DARK = "#16302A"
GREEN = "#1F4D3A"
GOLD = "#B08D3C"
EDGE = "#C9D3CC"


def build_graph(pairs: pd.DataFrame, herb_counts: pd.Series, min_lift: float = 1.2, top: int = 40) -> nx.Graph:
    g = nx.Graph()
    strong = pairs[pairs["lift"] >= min_lift].head(top)
    for r in strong.itertuples(index=False):
        g.add_edge(r.a, r.b, lift=float(r.lift), count=int(r.count))
    for node in g.nodes:
        g.nodes[node]["count"] = int(herb_counts.get(node, 0))
    return g


def neighbors(g: nx.Graph, herb: str) -> pd.DataFrame:
    if herb not in g:
        return pd.DataFrame(columns=["herb", "lift", "count"])
    rows = [{"herb": n, "lift": g[herb][n]["lift"], "count": g[herb][n]["count"]} for n in g[herb]]
    return pd.DataFrame(rows).sort_values("lift", ascending=False, ignore_index=True)


def figure(g: nx.Graph, highlight: str | None = None, seed: int = 3) -> go.Figure:
    fig = go.Figure()
    if g.number_of_nodes() == 0:
        fig.add_annotation(text="ไม่มีคู่ที่ผ่านเกณฑ์", showarrow=False)
        return _style(fig)

    pos = nx.spring_layout(g, seed=seed, weight="lift", k=1.2)
    max_lift = max(d["lift"] for _, _, d in g.edges(data=True))
    hl = set(g[highlight]) | {highlight} if highlight in g else set()

    for a, b, d in g.edges(data=True):
        on = highlight in (a, b)
        fig.add_trace(go.Scatter(
            x=[pos[a][0], pos[b][0]], y=[pos[a][1], pos[b][1]], mode="lines",
            line={"width": 1 + 5 * d["lift"] / max_lift, "color": GOLD if on else EDGE},
            hoverinfo="skip", showlegend=False,
        ))

    nodes = list(g.nodes)
    counts = [g.nodes[n]["count"] for n in nodes]
    biggest = max(counts) or 1
    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes],
        mode="markers+text", text=nodes, textposition="top center",
        textfont={"size": 14, "color": GREEN_DARK},
        marker={
            "size": [14 + 26 * c / biggest for c in counts],
            "color": [GREEN_DARK if n == highlight else (GREEN if n in hl or not hl else "#A9B8AE") for n in nodes],
            "line": {"width": 2, "color": "#FFFFFF"},
        },
        customdata=counts,
        hovertemplate="%{text}<br>%{customdata} ตำรับ<extra></extra>",
        showlegend=False,
    ))
    return _style(fig)


def _style(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        height=560, margin={"l": 10, "r": 10, "t": 10, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"visible": False}, yaxis={"visible": False},
        font={"family": "IBM Plex Sans Thai, sans-serif"},
    )
    return fig
