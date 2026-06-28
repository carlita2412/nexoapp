#!/usr/bin/env python
"""
Prueba de extremo a extremo del backend Nexo (Fase 1).

Recorre el flujo completo de un usuario final coordinador:
  1.  Healthcheck
  2.  Alta de organizaciones (reportante + 2 donantes)
  3.  Alta de item en el catalogo
  4.  Alta de centro de salud (con capacidades)
  5.  Reporte de una necesidad (triage critico, con requisitos de operacion)
  6.  Registro de dos donaciones disponibles
  7.  Matching: GET candidatos compatibles, ordenados por puntaje
  8.  Claim parcial (cobertura 3 de 5)
  9.  Claim que excede lo pendiente -> rechazado
  10. Claim que completa la necesidad -> cubierta
  11. Claim sobre necesidad ya cubierta -> rechazado
  12. Idempotencia: mismo idempotency_key dos veces -> ok / duplicado
  13. Pull por deltas

Uso:
    # Desde la raiz del repo (donde esta manage.py), con la BD migrada:
    python prueba_e2e.py

No necesita servidor corriendo: usa el cliente de pruebas de Django,
que ejecuta el mismo codigo real de URLs, middleware y vistas.
"""
import json
import os
import uuid

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nexo_backend.settings")
django.setup()

from django.test import Client  # noqa: E402

c = Client()
OK = "\033[92mOK\033[0m"
FAIL = "\033[91mFALLA\033[0m"
fallos = 0


def post(url, data):
    r = c.post(url, data=json.dumps(data), content_type="application/json")
    return r.status_code, (r.json() if r["Content-Type"].startswith("application/json") else {})


def get(url):
    r = c.get(url)
    return r.status_code, r.json()


def check(nombre, condicion):
    global fallos
    print(f"  [{OK if condicion else FAIL}] {nombre}")
    if not condicion:
        fallos += 1


print("=" * 60)
print("PRUEBA E2E — Backend Nexo")
print("=" * 60)

print("\n1) Healthcheck")
st, r = get("/api/v1/salud/")
check("GET /salud/ responde 200 y status ok", st == 200 and r["status"] == "ok")

print("\n2) Organizaciones")
_, reporta = post("/api/v1/organizaciones/", {"nombre": "Cruz Verde Caracas", "tipo": "ong", "verificada": True})
_, dona1 = post("/api/v1/organizaciones/", {"nombre": "Fundacion Salud Va", "tipo": "donante_privado", "verificada": True})
_, dona2 = post("/api/v1/organizaciones/", {"nombre": "Hospital Apoyo Norte", "tipo": "ong", "verificada": True})
check("3 organizaciones creadas", all("id" in o for o in (reporta, dona1, dona2)))

print("\n3) Catalogo")
_, item = post("/api/v1/catalogos/", {"codigo": "EQ-OXI-01", "nombre": "Concentrador de oxigeno", "categoria": "equipo_medico", "unidad": "unidad"})
check("Item de catalogo creado", "id" in item)

print("\n4) Centro de salud")
_, centro = post("/api/v1/centros-salud/", {
    "nombre": "Ambulatorio El Valle", "tipo": "ambulatorio", "estado_operativo": "parcial",
    "estado": "Miranda", "municipio": "El Valle",
    "tiene_electricidad": True, "tiene_agua": True, "tiene_oxigeno": True, "tiene_personal_tecnico": True})
check("Centro creado", "id" in centro)

print("\n5) Necesidad (5 uds, triage critico, requiere electricidad + oxigeno)")
_, nec = post("/api/v1/necesidades/", {
    "centro": centro["id"], "item": item["id"], "cantidad_solicitada": 5, "nivel_triage": "1_critico",
    "requisitos_operacion": {"requiere_electricidad": True, "requiere_oxigeno": True},
    "reportada_por": reporta["id"]})
check("Necesidad creada en estado 'abierta'", nec.get("estado") == "abierta")

print("\n6) Donaciones disponibles")
_, don1 = post("/api/v1/donaciones/", {"donante": dona1["id"], "item": item["id"], "cantidad": 3, "condicion": "nuevo", "estado": "disponible", "ubicacion_texto": "Galpon Chacao"})
_, don2 = post("/api/v1/donaciones/", {"donante": dona2["id"], "item": item["id"], "cantidad": 4, "condicion": "usado_funcional", "estado": "disponible", "ubicacion_texto": "Deposito Norte"})
check("2 donaciones disponibles", all("id" in d for d in (don1, don2)))

print("\n7) Matching: candidatos compatibles")
st, cand = get(f"/api/v1/necesidades/{nec['id']}/candidatos/")
puntajes = [x["puntaje"] for x in cand["candidatos"]]
check("Devuelve 2 candidatos", len(cand["candidatos"]) == 2)
check("Ordenados por puntaje (desc)", puntajes == sorted(puntajes, reverse=True))
check("Pendiente = 5", cand["cantidad_pendiente"] == 5)

print("\n8) Claim parcial (donante1 reclama 3 de 5)")
st, r = post(f"/api/v1/necesidades/{nec['id']}/claim/", {"donacion_id": don1["id"], "cantidad_asignada": 3, "organizacion_responsable_id": dona1["id"]})
check("Claim confirmado (HTTP 201)", st == 201 and r["estado"] == "confirmada")
st, cand = get(f"/api/v1/necesidades/{nec['id']}/candidatos/")
check("Pendiente baja a 2", cand["cantidad_pendiente"] == 2)

print("\n9) Claim que excede lo pendiente (4 sobre 2)")
st, r = post(f"/api/v1/necesidades/{nec['id']}/claim/", {"donacion_id": don2["id"], "cantidad_asignada": 4, "organizacion_responsable_id": dona2["id"]})
check("Rechazado (HTTP 400)", st == 400 and r["estado"] == "rechazada")

print("\n10) Claim que completa la necesidad (2 sobre 2)")
st, r = post(f"/api/v1/necesidades/{nec['id']}/claim/", {"donacion_id": don2["id"], "cantidad_asignada": 2, "organizacion_responsable_id": dona2["id"]})
check("Claim confirmado", st == 201 and r["estado"] == "confirmada")
st, cand = get(f"/api/v1/necesidades/{nec['id']}/candidatos/")
check("Pendiente = 0 y sin candidatos", cand["cantidad_pendiente"] == 0 and len(cand["candidatos"]) == 0)

print("\n11) Claim sobre necesidad ya cubierta")
st, r = post(f"/api/v1/necesidades/{nec['id']}/claim/", {"donacion_id": don2["id"], "cantidad_asignada": 1, "organizacion_responsable_id": dona2["id"]})
check("Rechazado", st == 400 and r["estado"] == "rechazada")

print("\n12) Idempotencia en /sync")
key = str(uuid.uuid4())
evento = {"eventos": [{"idempotency_key": key, "entity": "catalogo", "payload": {
    "id": str(uuid.uuid4()), "codigo": "INS-GUA-01", "nombre": "Guantes nitrilo", "categoria": "insumo", "unidad": "caja"}}]}
_, r1 = post("/api/v1/sync/", evento)
_, r2 = post("/api/v1/sync/", evento)
check("1er envio = ok", r1["resultados"][0]["estado"] == "ok")
check("Reintento = duplicado (no duplica)", r2["resultados"][0]["estado"] == "duplicado")

print("\n13) Pull por deltas")
st, deltas = get("/api/v1/sync/")
check("Devuelve cursor y deltas", "cursor" in deltas and "deltas" in deltas)

print("\n" + "=" * 60)
print(f"RESULTADO: {'TODO EN VERDE' if fallos == 0 else str(fallos) + ' FALLO(S)'}")
print("=" * 60)
raise SystemExit(1 if fallos else 0)