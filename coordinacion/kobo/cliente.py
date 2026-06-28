from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests
from django.conf import settings


class KoboError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConfiguracionKobo:
    api_url: str
    token: str
    limite: int = 500

    @classmethod
    def desde_settings(cls) -> "ConfiguracionKobo":
        return cls(
            api_url=getattr(settings, "KOBO_API_URL", "https://kf.kobotoolbox.org/api/v2").rstrip("/"),
            token=getattr(settings, "KOBO_TOKEN", ""),
            limite=int(getattr(settings, "KOBO_PULL_LIMIT", 500)),
        )


class ClienteKobo:
    def __init__(self, configuracion: ConfiguracionKobo | None = None):
        self.configuracion = configuracion or ConfiguracionKobo.desde_settings()

    def obtener_submissions(
        self,
        *,
        asset_uid: str,
        desde: datetime | None = None,
    ) -> list[dict[str, Any]]:
        if not asset_uid:
            raise KoboError("Falta asset_uid de KoBo.")
        if not self.configuracion.token:
            raise KoboError("Falta KOBO_TOKEN.")

        url = f"{self.configuracion.api_url}/assets/{asset_uid}/data/"
        query: dict[str, Any] = {}
        if desde:
            query["_submission_time"] = {"$gt": desde.isoformat()}

        respuesta = requests.get(
            url,
            headers={"Authorization": f"Token {self.configuracion.token}"},
            params={
                "limit": self.configuracion.limite,
                "sort": json.dumps({"_submission_time": 1, "_uuid": 1}),
                "query": json.dumps(query),
            },
            timeout=30,
        )

        if respuesta.status_code >= 400:
            raise KoboError(f"KoBo respondió {respuesta.status_code}: {respuesta.text[:300]}")

        data = respuesta.json()
        if isinstance(data, dict) and "results" in data:
            return list(data["results"])
        if isinstance(data, list):
            return data
        raise KoboError("Respuesta inesperada de KoBo.")
