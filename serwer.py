from fastapi import FastAPI
import random
import time

app = FastAPI()
#
@app.post("/receive")
def receive(data: dict):
    print("Dostałem:", data)
    offer = {
        "offer_id" : "a1b2c3",
        "price": random.randint(1,1000),
        "valid_seconds" : 30}
    return offer

client_decisions=[]
@app.post("/decision")
def decision_endpoint(data: dict):
    print("Dostałem decyzję klienta:", data)

    decision_record = {
        "offer_id": data.get("offer_id"),
        "accepted": data.get("decision"),
    }

    client_decisions.append(decision_record)

    print("Zapisana decyzja:", decision_record)
    print("Wszystkie decyzje:", client_decisions)

    return {
        "status": "decision received",
        "saved_decision": decision_record
    }

