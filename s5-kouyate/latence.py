import sys, time, requests, numpy as np
port, img = sys.argv[1], sys.argv[2]
def appel():
    with open(img, "rb") as f:
        t = time.perf_counter()
        r = requests.post(f"http://localhost:{port}/predict", files={"image": f})
        return (time.perf_counter() - t) * 1000, r.status_code
for _ in range(5): appel()
m = [appel() for _ in range(50)]
ms = [x[0] for x in m]
print("codes :", {c for _, c in m}, " p50 :", round(np.percentile(ms, 50), 1), " p95 :", round(np.percentile(ms, 95), 1))
