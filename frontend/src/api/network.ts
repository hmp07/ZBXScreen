import request from "./request";

export function getNetworkDashboard() {
  return request.get("/network/dashboard");
}
