"""Sample payloads that mimic the shape of the Dongfeng eπ TSP responses.

Used by mock_mode so the dashboard can be demoed without real credentials.
Field names follow those recovered from classes.dex and the ADS protobuf
definitions (powerSocStatus / chargingStatus / acCabinTemperature ...).
"""

MOCK_VEHICLE_STATUS = {
    "code": "000000",
    "msg": "success",
    "traceId": "mock-trace",
    "data": {
        "vin": "LGB00000000000001",
        "online": 1,
        "updateTime": "2026-10-18 12:34:56",
        "powerSocStatus": 72,
        "batteryStateSoc": 72,
        "enduranceMileage": 412,
        "totalMileage": 8642.5,
        "chargingStatus": 1,
        "acChargeStatus": 1,
        "batteryPackChrgDchrgPower": 6500,
        "batteryPackChrgDchrgTimeLength": 48,
        "chargingPortStatus": 1,
        "lockStatus": 1,
        "doorStatus": {
            "leftFront": 0,
            "rightFront": 0,
            "leftRear": 0,
            "rightRear": 0,
            "trunk": 0,
            "bonnet": 0,
        },
        "windowStatus": 0,
        "rearViewMirrorStatus": 1,
        "airCondition": {
            "acStatus": 1,
            "acCabinTemperature": 22.5,
            "outTemperature": 15.0,
            "acSetTemprature": 24,
        },
        "speed": 0,
        "gear": 0,
        "location": {
            "longitude": 116.397428,
            "latitude": 39.90923,
            "positionTime": "2026-10-18 12:33:10",
        },
        "tyrePressure": {
            "leftFront": 245,
            "rightFront": 246,
            "leftRear": 243,
            "rightRear": 244,
        },
    },
}
