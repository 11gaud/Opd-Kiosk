SESSION_KEY = 'kiosk'


class KioskSession:
    """Typed wrapper around request.session for wizard state."""

    def __init__(self, request):
        self._request = request
        if SESSION_KEY not in request.session:
            request.session[SESSION_KEY] = {}

    def _data(self):
        return self._request.session[SESSION_KEY]

    def get(self, key, default=None):
        return self._data().get(key, default)

    def set(self, key, value):
        self._data()[key] = value
        self._request.session.modified = True

    def update(self, data: dict):
        self._data().update(data)
        self._request.session.modified = True

    def clear(self):
        self._request.session[SESSION_KEY] = {}
        self._request.session.modified = True

    @property
    def current_step(self) -> int:
        return self._data().get('step', 1)

    def advance_to(self, step: int):
        self._data()['step'] = step
        self._request.session.modified = True
