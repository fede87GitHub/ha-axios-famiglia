DOMAIN = "axios_famiglia"

CONF_CUSTOMER_ID = "customer_id"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_STUDENT_NAME = "student_name"

# Usato per le entry create prima della v1.0.3 (nessun nome studente salvato)
DEFAULT_STUDENT_NAME = "famiglia"

DEFAULT_SCAN_INTERVAL = 30  # minuti

# Quanti giorni di registro tenere (compiti, annotazioni, note)
REGISTER_DAYS = 14
# Quante comunicazioni esporre nell'attributo "elenco"
COMMUNICATIONS_LIMIT = 20
# Timeout totale per ogni richiesta HTTP (secondi)
REQUEST_TIMEOUT = 30

# User-Agent dichiarato. Se Axios dovesse rifiutarlo (HTTP 400/403 al login),
# il valore precedente funzionante era "curl/8.14.1".
USER_AGENT = "HomeAssistant-AxiosFamiglia (+https://github.com/fapozzi/ha-axios-famiglia)"

BASE_URL = "https://registrofamiglie.axioscloud.it"
LOGIN_PATH = "/Pages/SD/SD_Login.aspx"
DASHBOARD_PATH_HINT = "SD_Dashboard.aspx"
AJAX_PATH = "/Pages/APP/APP_Ajax_Get.aspx"

# Azioni che il browser esegue automaticamente subito dopo il caricamento
# della dashboard, PRIMA di qualunque azione dell'utente (viste nella
# cattura HAR). Confermato con test standalone (ottobre 2026): senza
# questa sequenza, la prima chiamata applicativa (es.
# FAMILY_COMUNICAZIONI) viene rifiutata dal server con un secco
# "HTTP 400 Bad Request" a corpo vuoto, anche con login, cookie e token
# anti-CSRF tutti corretti.
DASHBOARD_INIT_ACTIONS = ["HeaderLoad", "FooterLoad", "DashboardLoad"]

PLATFORMS = ["sensor"]