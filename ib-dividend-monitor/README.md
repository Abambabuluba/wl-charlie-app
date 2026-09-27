# divmon: monitor de cartera de dividendos en Interactive Brokers

Vigila tu cartera real de IBKR, analiza y te **propone** acciones por email (o Telegram) y en un informe semanal.
**Nunca envía órdenes**: todas las operaciones las decides y ejecutas tú.

| Función | Qué hace |
|---|---|
| Resumen de cartera | Posiciones, pesos, exposición por país, sector y divisa (neta de préstamos), plusvalías, rentabilidad actual y sobre coste |
| Margen | Préstamo por divisa, intereses estimados y el último cargo real, colchón, caída de la cartera que provocaría margin call |
| Dividendos | Calendario de próximos cobros (anunciados y estimados), ingresos previstos por mes y año, histórico de cobros netos de retenciones |
| Plan de amortización | Meses hasta deuda cero con tu aportación mensual (500 €) más dividendos, comparado con "solo aportaciones" |
| Radar | Avisa cuando una candidata pasa a cumplir tus criterios o cuando una posición deja de cumplirlos |
| Concentración | Avisa si una posición, país, sector o divisa supera tus límites |

## Cómo obtiene los datos (y por qué es de solo lectura)

```
IBKR Flex Web Service ──(XML diario)──┐
Yahoo Finance (fundamentales) ────────┼──> divmon ──> SQLite (histórico)
IB Gateway (opcional, margen en vivo) ┘        ├──> Email o Telegram (alertas)
                                               └──> Informe HTML/PDF semanal
```

- **Flex Web Service** es la fuente principal. IBKR genera un informe con posiciones, efectivo, dividendos, retenciones, intereses y dividendos anunciados. Solo se descarga con un token: **no hay forma de operar con él** y no necesita IB Gateway ni reautenticaciones.
- **Yahoo Finance** aporta PER, payout, deuda/EBITDA y sector. Es gratuito pero no oficial. Cualquier dato se puede fijar a mano en `config.yaml`.
- **IB Gateway es opcional** y solo sirve para ver el margen exacto en tiempo real. Si lo usas, está blindado en tres capas: el Gateway en modo "Read-Only API", la conexión con `readonly=True` y una clase que solo permite métodos de consulta. Un test (`tests/test_readonly.py`) falla si en el código aparece cualquier método de órdenes.

La cartera se mueve poco, así que basta con una ejecución diaria y los fundamentales se refrescan una vez por semana.

## Instalación

Necesitas Python 3.10 o superior.

```bash
cd ib-dividend-monitor
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env
cp config.example.yaml config.yaml
```

Extras opcionales: `pip install -e ".[pdf]"` para informes en PDF y `pip install -e ".[gateway]"` para IB Gateway.

## 1. Probar sin tocar tu cuenta

El repositorio incluye un informe Flex ficticio. En `config.yaml` pon `alerts.channel: console` (así nada sale de tu ordenador) y ejecuta:

```bash
divmon daily --xml tests/fixtures/flex_sample.xml --dry-run   # análisis y alertas por pantalla
divmon daily --xml tests/fixtures/flex_sample.xml             # lo guarda en data/ como si fuera real
divmon report                                                 # data/reports/informe-AAAA-MM-DD.html
divmon plan
```

Cuando termines de probar, borra la carpeta `data/` para no mezclar los datos ficticios con los tuyos.

## 2. Configurar la Flex Query en IBKR

En el Portal de IBKR ve a **Rendimiento e informes → Flex Queries** y crea una **Activity Flex Query** con:

| Sección | Opciones |
|---|---|
| Account Information | todos los campos |
| Open Positions | *Summary*; incluye `listingExchange`, `isin`, `issuerCountryCode`, `costBasisMoney` |
| Cash Report | todos los campos |
| Cash Transactions | Dividends, Payment In Lieu of Dividends, Withholding Tax, Broker Interest Paid/Received. Nivel de detalle: *Detail* |
| Open Dividend Accruals | todos los campos |
| Conversion Rates | todos los campos |

Configuración de entrega:
- Formato **XML**.
- Periodo **Last 365 Calendar Days**.
- Formato de fecha **yyyyMMdd**, formato de hora **HHmmss** y separador **;**.

Después, en **Flex Queries → Flex Web Service Configuration**, activa el servicio y genera un **token**. Copia el token y el **Query ID** (aparece en la lista de consultas) en `.env`. El token caduca, como mucho, al cabo de un año. Cuando caduque, divmon te avisará por el canal de alertas que uses.

La primera ejecución carga el último año de dividendos. Para cargar años anteriores, descarga informes de esos años desde el Portal (periodo personalizado) e impórtalos:

```bash
divmon import-history cobros-2023.xml cobros-2024.xml
```

## 3. Alertas por email (Gmail)

Gmail no deja usar tu contraseña normal desde programas: hace falta una **contraseña de aplicación**. Solo sirve para enviar correo y la puedes revocar cuando quieras.

1. Activa la **verificación en dos pasos** en tu cuenta de Google (myaccount.google.com → Seguridad), si no la tienes ya.
2. Entra en **myaccount.google.com/apppasswords**, escribe un nombre (por ejemplo `divmon`) y pulsa **Crear**.
3. Google te muestra una contraseña de 16 letras. Cópiala: solo se enseña una vez.
4. En `.env` pon:
   ```
   SMTP_USER=tu_correo@gmail.com
   SMTP_PASSWORD=la contraseña de 16 letras
   EMAIL_TO=tu_correo@gmail.com
   ```
5. En `config.yaml` deja `alerts.channel: email` y prueba con:
   ```bash
   divmon test-notify
   ```

Todas las alertas de una ejecución llegan en un solo correo. El asunto empieza por 🔴 si alguna es crítica. El informe semanal llega adjunto al correo del resumen.

## 3 bis. Alternativa: bot de Telegram

1. En Telegram, abre **@BotFather** y envía `/newbot`.
2. Elige un nombre y un usuario que termine en `bot` (por ejemplo `micartera_alertas_bot`). BotFather te dará un **token** del tipo `123456:ABC-...`.
3. Abre el chat con tu bot nuevo y envíale cualquier mensaje (por ejemplo `/start`).
4. En el navegador, abre `https://api.telegram.org/bot<TOKEN>/getUpdates` y busca `"chat":{"id":123456789`. Ese número es tu **chat_id**.
5. Pon `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env`, pon `alerts.channel: telegram` en `config.yaml` y prueba con:

```bash
divmon test-notify
```

El bot solo escribe a tu `chat_id`. No compartas el token: quien lo tenga puede enviar mensajes en nombre del bot, aunque no puede tocar tu cuenta de IBKR.

## 4. Ajustar config.yaml

Todo está comentado en `config.example.yaml`. Lo principal:

- `criteria`: PER máximo, rentabilidad mínima, payout máximo y deuda/EBITDA máximo.
- `margin.interest_rates`: el tipo que te cobra IBKR por divisa. Revísalo de vez en cuando, porque cambia con los tipos de referencia.
- `margin.alerts`: umbrales de préstamo/valor, colchón mínimo y caída mínima hasta margin call.
- `concentration`: límites por posición, país, sector y divisa.
- `amortization.monthly_contribution: 500`.
- `radar.candidates`: tus candidatas (símbolo de IBKR y, si hace falta, el de Yahoo).
- `symbols`: ajustes por valor. Por ejemplo, desactivar el payout en REITs, fijar el sector o el margen de mantenimiento propio de un valor, o introducir un dato fundamental a mano.

## Comandos

| Comando | Para qué |
|---|---|
| `divmon daily [--dry-run]` | Descarga el Flex, analiza, guarda el histórico y envía las alertas nuevas |
| `divmon report [--send] [--pdf]` | Genera el informe semanal y, con `--send`, lo envía por email o Telegram |
| `divmon summary` | Resumen por pantalla con posiciones y radar |
| `divmon plan [--aportacion 600]` | Tabla de meses hasta deuda cero según la aportación |
| `divmon margin-live [--dry-run]` | Margen exacto vía IB Gateway (opcional) |
| `divmon import-history FICHEROS...` | Carga cobros antiguos |
| `divmon test-notify` | Mensaje de prueba por el canal configurado |

Las alertas no se repiten antes de `alerts.cooldown_hours` (72 h por defecto). El radar solo avisa cuando cambia el estado de un valor.

## Programar las ejecuciones

- **Linux/macOS (cron):** copia las líneas de `deploy/crontab.example` con `crontab -e` y ajusta la ruta. `deploy/run.sh` entra en la carpeta, usa `.venv` y guarda un log en `data/logs/`.
- **Windows:** ejecuta `powershell -ExecutionPolicy Bypass -File deploy\windows_tasks.ps1`. Las tareas se ejecutan al encender el PC si estaba apagado a la hora prevista.

Calendario propuesto (hora de Madrid):
- `daily`: de martes a sábado a las 07:40.
- `report --send`: los sábados a las 09:10.

Sin IB Gateway no hay reautenticaciones de las que preocuparse: Flex solo necesita el token.

### Si activas IB Gateway (margen en tiempo real)

1. En IB Gateway, ve a **Configure → Settings → API → Settings** y marca **Read-Only API**. Pon el puerto 4002 para paper trading o 4001 para la cuenta real.
2. Lo más seguro es crear en el Portal un **usuario secundario sin permisos de trading** y usarlo solo aquí.
3. IB Gateway se reinicia a diario y pide un login completo con 2FA una vez por semana (normalmente el domingo). [IBC](https://github.com/IbcAlpha/IBC) automatiza el login y el reinicio diario. El 2FA semanal lo apruebas tú en IBKR Mobile.
4. Si el Gateway no responde, divmon te avisa una vez ("¿toca reautenticar?") y sigue funcionando con el margen estimado.
5. Empieza con la cuenta paper (`port: 4002`) y `divmon margin-live --dry-run`. Pasa al puerto 4001 cuando veas que todo cuadra.

## Alerta nativa de margen de IBKR (recomendada)

Como red de seguridad adicional, IBKR puede vigilar tu *margin cushion* 24/7 con una alerta propia que te llega por email, aunque tu ordenador esté apagado. Se crea desde IBKR Desktop o pidiéndoselo a Claude con el conector de IBKR. Estas alertas solo se ven en IBKR Desktop.

Si usas el conector de IBKR en Claude, puedes desactivar sus herramientas de órdenes (`create_order_instruction` y similares) en la configuración de conectores de claude.ai para que solo lea.

## Limitaciones conocidas

- **Margen estimado:** sin IB Gateway, el margen de mantenimiento se estima con un porcentaje (25 % por defecto). IBKR puede exigir más en algunos valores o en momentos de volatilidad. Usa `symbols.<X>.maintenance_rate` para afinarlo y la alerta nativa de IBKR como respaldo.
- **Dividendos estimados:** se proyectan repitiendo los pagos del último año con tus acciones actuales. Los dividendos anunciados por la empresa sustituyen a la estimación. Los valores sin historial usan la rentabilidad de Yahoo, repartida por igual entre los 12 meses.
- **Exposición por país:** se basa en el domicilio del emisor (código de país de IBKR o prefijo del ISIN), no en dónde facturan las empresas.
- **Yahoo Finance:** puede cambiar sin aviso o dejar huecos. Si falla con un valor, divmon lo registra y sigue con el resto.

## Tests

```bash
pip install -e ".[dev]"
pytest
```
