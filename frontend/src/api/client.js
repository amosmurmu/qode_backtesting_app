import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // backtests over many years/stocks can take a few seconds
});

export async function runBacktest(payload) {
  const { data } = await client.post("/backtest", payload);
  return data;
}

export async function getAvailableMetrics() {
  const { data } = await client.get("/metrics/available");
  return data;
}

export async function getDataCoverage() {
  const { data } = await client.get("/data-coverage");
  return data;
}

export async function getStocks() {
  const { data } = await client.get("/stocks");
  return data;
}

export default client;
