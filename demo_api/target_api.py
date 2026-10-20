"""
Demo target API -- a deliberately flawed "PetStore-style" service used as the
system under test for the AI-Powered Intelligent API Testing Platform.

Seeded defects (ground truth for evaluation) are declared in SEEDED_DEFECTS.
Every defect is real and reachable; the testing platform is not told about them.
"""
from flask import Flask, request, jsonify
import time
import random
import threading

app = Flask(__name__)

# ----------------------------------------------------------------------------
# Ground-truth defect register. The platform never reads this -- it is used
# ONLY by the evaluation script to compute defect-detection rate.
# ----------------------------------------------------------------------------
SEEDED_DEFECTS = {
    "D1": {
        "endpoint": "GET /pets/{petId}",
        "category": "validation",
        "description": "Negative / non-integer petId returns 500 instead of 400",
    },
    "D2": {
        "endpoint": "POST /pets",
        "category": "validation",
        "description": "Missing required 'name' field is accepted with 201 instead of 400",
    },
    "D3": {
        "endpoint": "GET /orders/{orderId}",
        "category": "security-bola",
        "description": "Broken object-level authorization: any authenticated user can read any order",
    },
    "D4": {
        "endpoint": "GET /pets",
        "category": "performance",
        "description": "Latency degrades severely when limit parameter is large (no pagination cap)",
    },
    "D5": {
        "endpoint": "POST /pets",
        "category": "validation",
        "description": "Oversized name (>256 chars) causes unhandled 500",
    },
    "D6": {
        "endpoint": "GET /pets/search",
        "category": "security-injection",
        "description": "SQL-like injection payload is echoed back unsanitised in an error trace",
    },
    "D7": {
        "endpoint": "DELETE /pets/{petId}",
        "category": "auth",
        "description": "Missing auth token is accepted -- endpoint does not enforce authentication",
    },
    "D8": {
        "endpoint": "GET /pets/{petId}",
        "category": "schema",
        "description": "For petId>900 the response omits the required 'status' field (schema drift)",
    },
}

_PETS = {
    i: {"id": i, "name": f"pet-{i}", "tag": random.choice(["dog", "cat", "bird"]), "status": "available"}
    for i in range(1, 51)
}
_ORDERS = {
    i: {"id": i, "petId": (i % 50) + 1, "ownerId": 100 + (i % 3), "quantity": (i % 4) + 1}
    for i in range(1, 21)
}
_LOCK = threading.Lock()


def _auth_user():
    """Returns the user id from the bearer token, or None."""
    tok = request.headers.get("Authorization", "")
    if tok.startswith("Bearer user-"):
        try:
            return int(tok.split("user-")[1])
        except ValueError:
            return None
    return None


@app.route("/pets", methods=["GET"])
def list_pets():
    limit = request.args.get("limit", "20")
    try:
        limit = int(limit)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400
    if limit < 0:
        return jsonify({"error": "limit must be non-negative"}), 400

    # --- D4: no cap on limit; latency grows without bound -------------------
    if limit > 100:
        time.sleep(min(0.004 * limit, 3.0))  # pathological slow path

    items = list(_PETS.values())[:limit]
    return jsonify({"items": items, "count": len(items)}), 200


@app.route("/pets/search", methods=["GET"])
def search_pets():
    q = request.args.get("q", "")
    # --- D6: reflects unsanitised input inside an error trace ---------------
    if any(tok in q.lower() for tok in ["'", "--", " or ", "union", ";"]):
        return jsonify({
            "error": "query failed",
            "trace": f"SELECT * FROM pets WHERE name LIKE '%{q}%'",
        }), 500
    matches = [p for p in _PETS.values() if q.lower() in p["name"].lower()]
    return jsonify({"items": matches, "count": len(matches)}), 200


@app.route("/pets/<petId>", methods=["GET"])
def get_pet(petId):
    # --- D1: no input validation; int() raises -> 500 -----------------------
    pid = int(petId)          # ValueError on "abc" -> unhandled 500
    if pid < 0:
        raise ValueError("negative id")   # -> unhandled 500

    pet = _PETS.get(pid)
    if pet is None:
        # --- D8: schema drift for high ids ---------------------------------
        if pid > 900:
            return jsonify({"id": pid, "name": "ghost", "tag": "unknown"}), 200
        return jsonify({"error": "not found"}), 404
    return jsonify(pet), 200


@app.route("/pets", methods=["POST"])
def create_pet():
    body = request.get_json(silent=True) or {}
    name = body.get("name")

    # --- D5: oversized name is not guarded ---------------------------------
    if name is not None and len(name) > 256:
        _ = _PETS[999999]     # KeyError -> unhandled 500

    # --- D2: required field not enforced -----------------------------------
    with _LOCK:
        new_id = max(_PETS) + 1
        _PETS[new_id] = {
            "id": new_id,
            "name": name,                       # may be None -- accepted anyway
            "tag": body.get("tag", "unknown"),
            "status": "available",
        }
    return jsonify(_PETS[new_id]), 201


@app.route("/pets/<int:petId>", methods=["DELETE"])
def delete_pet(petId):
    # --- D7: no authentication check at all --------------------------------
    with _LOCK:
        _PETS.pop(petId, None)
    return jsonify({"deleted": petId}), 200


@app.route("/orders/<int:orderId>", methods=["GET"])
def get_order(orderId):
    user = _auth_user()
    if user is None:
        return jsonify({"error": "unauthorized"}), 401
    order = _ORDERS.get(orderId)
    if order is None:
        return jsonify({"error": "not found"}), 404
    # --- D3: BOLA -- ownerId is never compared against the caller ----------
    return jsonify(order), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5099, threaded=True)
