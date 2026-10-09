DOMAIN = "axios_famiglia"

# --- Dati di accesso (config entry) ---
CONF_CUSTOMER_ID = "customer_id"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_STUDENT_NAME = "student_name"

# --- Opzioni modificabili dall'utente (options flow) ---
CONF_SCAN_INTERVAL = "scan_interval"  # minuti
CONF_REGISTER_DAYS = "register_days"  # giorni di registro da considerare
CONF_COMMUNICATIONS_LIMIT = "communications_limit"  # comunicazioni esposte
CONF_REQUEST_TIMEOUT = "request_timeout"  # secondi

DEFAULT_SCAN_INTERVAL = 30
DEFAULT_REGISTER_DAYS = 14
DEFAULT_COMMUNICATIONS_LIMIT = 20
DEFAULT_REQUEST_TIMEOUT = 30

# Intervalli accettati dal pannello delle opzioni.
# - SCAN_INTERVAL: almeno 5 minuti, per non sovraccaricare il portale.
# - COMMUNICATIONS_LIMIT: al massimo 50, perché l'elenco è un attributo del sensore e
#   Home Assistant non salva nello storico attributi più grandi di circa 16 KB.
MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL = 5, 1440
MIN_REGISTER_DAYS, MAX_REGISTER_DAYS = 1, 90
MIN_COMMUNICATIONS_LIMIT, MAX_COMMUNICATIONS_LIMIT = 1, 50
MIN_REQUEST_TIMEOUT, MAX_REQUEST_TIMEOUT = 10, 120

# User-Agent dichiarato. Se Axios dovesse rifiutarlo (HTTP 400/403 al login),
# il valore precedente funzionante era "curl/8.14.1".
USER_AGENT = "HomeAssistant-AxiosFamiglia (+https://github.com/fede87GitHub/ha-axios-famiglia)"

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

PLATFORMS = ["sensor", "calendar", "event"]
