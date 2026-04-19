"""
connector/base.py
=================
Transporte HTTP JSON-RPC, autenticación y execute_kw.

Todos los demás mixins del connector dependen de execute_kw() definido aquí.
No importa ningún modelo Django — es puro I/O contra Odoo.
"""
import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OdooBaseConnector:
    """
    Capa de transporte HTTP y autenticación para Odoo JSON-RPC.

    Ciclo de vida de una instancia:
      1. __init__ carga credenciales desde settings o parámetros explícitos.
      2. La primera llamada a self.uid dispara _authenticate() y guarda el UID
         junto con las cookies de sesión en self._session.
      3. execute_kw() usa el UID y el session cookie en cada llamada.
      4. Si Odoo retorna "Session Expired", execute_kw reautentica una vez y reintenta.

    UID vs Redis cache:
      El UID NO se cachea en Redis porque está acoplado a las cookies de sesión
      almacenadas en self._session. Reutilizar un UID de otra instancia (o de
      una instancia anterior) sin sus cookies produciría "Session Expired"
      en todas las llamadas siguientes. La autenticación tarda ~50 ms y ocurre
      una sola vez por instancia, por lo que self._uid es suficiente.
    """

    def __init__(self, url=None, db_name=None, username=None, password=None):
        self.url = (url or settings.ODOO_CONFIG.get('URL', 'http://odoo:8069')).rstrip('/')
        self.db_name = db_name or settings.ODOO_CONFIG.get('DB', 'ecomparts_odoo_shared')
        self.username = username or settings.ODOO_CONFIG.get('USERNAME', 'admin')
        self.password = password or settings.ODOO_CONFIG.get('PASSWORD', 'admin')
        self.timeout = float(settings.ODOO_CONFIG.get('TIMEOUT', 30))
        self._uid = None
        self._session = requests.Session()
        self._session.headers.update({'Content-Type': 'application/json'})

    # ── Transporte ─────────────────────────────────────────────────────────────

    def _call(self, endpoint: str, params: dict):
        """
        Realiza una llamada JSON-RPC a Odoo.

        Args:
            endpoint: Endpoint relativo (ej: /web/session/authenticate)
            params:   Parámetros del método RPC

        Returns:
            El campo 'result' de la respuesta JSON

        Raises:
            Exception: Si Odoo devuelve un error JSON-RPC o hay error de red
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": params,
        }

        try:
            response = self._session.post(
                f"{self.url}{endpoint}",
                data=json.dumps(payload),
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                error = result["error"]
                raise Exception(
                    f"Odoo JSON-RPC error {error.get('code')}: "
                    f"{error.get('message')} — {error.get('data', {}).get('message', '')}"
                )

            return result.get("result")

        except requests.exceptions.RequestException as e:
            logger.exception("Error de red conectando a Odoo %s: %s", self.url, e)
            raise

    # ── Autenticación ──────────────────────────────────────────────────────────

    @property
    def uid(self):
        """UID autenticado. Se autentica la primera vez que se accede."""
        if self._uid:
            return self._uid
        return self._authenticate()

    def _authenticate(self):
        """Autentica contra Odoo y almacena el UID en self._uid."""
        try:
            result = self._call("/web/session/authenticate", {
                "db": self.db_name,
                "login": self.username,
                "password": self.password,
            })

            uid = result.get("uid") if result else None

            if uid:
                self._uid = uid
                logger.info("Conectado a Odoo %s como %s (UID: %s)", self.url, self.username, uid)
                return uid
            else:
                logger.error("Falló autenticación en Odoo para %s", self.username)
                return None

        except Exception as e:
            logger.exception("Error autenticando en Odoo: %s", e)
            return None

    # ── ORM bridge ────────────────────────────────────────────────────────────

    def execute_kw(self, model: str, method: str, args=None, kwargs=None):
        """
        Ejecuta un método ORM en Odoo via JSON-RPC (/web/dataset/call_kw).

        El context siempre incluye tz=America/Lima. Si el llamador pasa su
        propio context dentro de kwargs, se fusiona (el llamador tiene prioridad).

        Reintenta una vez si la sesión expiró entre llamadas.

        Args:
            model:  Nombre del modelo Odoo (ej: 'res.company')
            method: Método a ejecutar (ej: 'search_read', 'create', 'write')
            args:   Argumentos posicionales (lista)
            kwargs: Argumentos nombrados (fields, limit, domain, context, etc.)

        Returns:
            Resultado del método ejecutado en Odoo

        Raises:
            Exception: Si no se puede autenticar o si Odoo devuelve error
        """
        if not self.uid:
            raise Exception("No se pudo autenticar con Odoo")

        args = args or []
        kwargs = kwargs or {}

        caller_context = kwargs.pop('context', {})
        merged_context = {'tz': 'America/Lima', **caller_context}

        def _do_call():
            return self._call("/web/dataset/call_kw", {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": {**kwargs, "context": merged_context},
            })

        try:
            return _do_call()
        except Exception as e:
            err_msg = str(e).lower()
            if 'session expired' in err_msg or 'session_invalid' in err_msg:
                logger.warning(
                    "Sesion Odoo expirada en %s/%s. Reautenticando y reintentando...",
                    method,
                    model,
                )
                self._uid = None
                if self._authenticate():
                    return _do_call()

            logger.exception("Error ejecutando %s en %s: %s", method, model, e)
            raise

    # ── Health check ──────────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Verifica que la conexión a Odoo responde. True si OK."""
        try:
            result = self._call("/web/dataset/call_kw", {
                "model": "res.lang",
                "method": "search_read",
                "args": [[]],
                "kwargs": {"fields": ["id"], "limit": 1},
            })
            return result is not None
        except Exception:
            return False
