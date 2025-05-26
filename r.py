import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime
import requests

# Streamlit Page Config
st.set_page_config(page_title="Rakshini Navigator", layout="centered")

# Telegram Bot Config
BOT_TOKEN = st.secrets["BOT_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]

# Load Graph from CSV
@st.cache_data
def load_graph_from_csv(csv_path):
    df = pd.read_csv(csv_path)
    graph = {}
    for _, row in df.iterrows():
        src, dst = row["Source"], row["Destination"]
        danger, distance = row["DangerScore"], row["Distance"]
        graph.setdefault(src, {})[dst] = {"danger": danger, "distance": distance}
        graph.setdefault(dst, {})[src] = {"danger": danger, "distance": distance}
    return graph, list(set(df["Source"]).union(set(df["Destination"])))

graph, all_locations = load_graph_from_csv("graph_data.csv")

# Dijkstra Algorithm
def dijkstra(graph, start, end):
    G = nx.Graph()
    for u in graph:
        for v in graph[u]:
            G.add_edge(u, v, weight=graph[u][v]["danger"])
    try:
        path = nx.dijkstra_path(G, start, end, weight='weight')
        total_risk = sum(graph[path[i]][path[i+1]]["danger"] for i in range(len(path)-1))
        total_distance = sum(graph[path[i]][path[i+1]]["distance"] for i in range(len(path)-1))
        return path, total_risk, total_distance
    except:
        return None, None, None

# Send Telegram Alert
def send_telegram_alert(user_name, location):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"""
🚨 EMERGENCY ALERT 🚨
Name: {user_name}
Location: {location}
Time: {timestamp}
Please respond immediately!
"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(url, data=payload)
    return response.ok

# Plot Graph
def plot_graph_with_path(graph, path, pointer_index=None):
    G = nx.Graph()
    for node in graph:
        for neighbor in graph[node]:
            G.add_edge(node, neighbor, weight=graph[node][neighbor]["danger"])

    pos = nx.spring_layout(G, seed=42)

    plt.figure(figsize=(10, 6))
    nx.draw(G, pos, with_labels=True, node_color='lightblue', edge_color='gray',
            node_size=1000, font_size=10)
    if path and len(path) > 1:
        edges_in_path = [(path[i], path[i+1]) for i in range(len(path)-1)]
        nx.draw_networkx_edges(G, pos, edgelist=edges_in_path, width=2.5, edge_color='green')

    if pointer_index is not None and path and pointer_index < len(path):
        nx.draw_networkx_nodes(G, pos, nodelist=[path[pointer_index]], node_color='red', node_size=1200)

    st.pyplot(plt.gcf())
    plt.close()

# Session State
if "path" not in st.session_state:
    st.session_state.path = None
if "pointer_index" not in st.session_state:
    st.session_state.pointer_index = -1

# UI
st.title("🛡 Rakshini - Safe Route Navigator")

col1, col2 = st.columns(2)
with col1:
    source = st.selectbox("Source", all_locations)
with col2:
    destination = st.selectbox("Destination", all_locations)

if st.button("🔍 Find Safest Route"):
    if source == destination:
        st.warning("Source and destination must be different.")
    else:
        path, risk, distance = dijkstra(graph, source, destination)
        if path:
            st.success("Safest Path: " + " → ".join(path))
            st.info(f"Total Risk Score: {risk}")
            st.info(f"Total Distance: {distance:.2f} km")
            st.session_state.path = path
            st.session_state.pointer_index = -1
        else:
            st.error("No valid path found.")

# Simulation Controls
if st.session_state.path:
    col_sim1, col_sim2 = st.columns(2)
    with col_sim1:
        if st.button("▶️ Start / Restart Simulation"):
            st.session_state.pointer_index = 0
    with col_sim2:
        if st.button("⏩ Next Step"):
            if st.session_state.pointer_index < len(st.session_state.path) - 1:
                st.session_state.pointer_index += 1
            else:
                st.success("🏁 Simulation Completed!")

    # Display current location
    current_pos = st.session_state.pointer_index
    if current_pos != -1:
        current_location = st.session_state.path[current_pos]
        st.write(f"🧭 Current Location: {current_location}")
        plot_graph_with_path(graph, st.session_state.path, pointer_index=current_pos)
    else:
        st.write("🧭 Simulation not started.")
        plot_graph_with_path(graph, st.session_state.path)

# Emergency Button (sends alert for current location only)
if st.session_state.path and st.session_state.pointer_index != -1:
    current_location = st.session_state.path[st.session_state.pointer_index]
else:
    current_location = source  # fallback if simulation hasn't started

if st.button("🚨 Send Emergency Alert"):
    success = send_telegram_alert("Ananya Sharma", current_location)
    if success:
        st.warning(f"🚨 Alert sent with location: {current_location}.")
    else:
        st.error("❌ Failed to send alert. Check bot setup.")
