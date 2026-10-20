# Google Places: control de gasto

## Qué hace
1. **Contador interno** (`google_api_usage`): cada llamada real a Places registra su SKU. Sobrevive a los deploys.
2. **Gasto real**: lee la exportación de Cloud Billing en BigQuery y guarda el neto diario por SKU en `google_spend_daily`.
3. **Estimación previa** (`POST /api/scraper/estimate`): llamadas por SKU y USD esperados, descontando el gratis mensual y aplicando los tramos de precio con el uso acumulado del mes.
4. **Límite mensual**: `POST /api/scraper/run` responde **409** si el gasto del mes + el scrape supera `GOOGLE_SPEND_LIMIT_USD`. El frontend pide confirmación y reintenta con `force=true`.

Endpoints: `GET /api/google-spend/summary`, `POST /api/google-spend/sync` (botón «Actualizar»), `POST /api/scraper/estimate`.

## Variables de entorno (Railway → Variables)
| Variable | Para qué |
|---|---|
| `GOOGLE_BILLING_BQ_TABLE` | `proyecto.dataset.gcp_billing_export_v1_XXXXXX` |
| `GOOGLE_BILLING_SA_JSON` | JSON completo de la cuenta de servicio, en una línea |
| `GOOGLE_SPEND_LIMIT_USD` | Límite mensual (default 10) |
| `GOOGLE_SPEND_WARN_USD` | Umbral para pedir confirmación (default 2) |

Sin las dos primeras, el gasto real aparece como «Facturación no conectada» (nunca como $0); el contador interno y el límite funcionan igual, basados en la estimación.

## Activar la exportación de facturación (una sola vez)
1. Google Cloud → **Billing** → tu cuenta de facturación → **Billing export** → **BigQuery export**.
2. Crea (o elige) un dataset de BigQuery y activa **Standard usage cost**. La tabla se llamará `gcp_billing_export_v1_XXXXXX_XXXXXX_XXXXXX`.
3. Crea una **cuenta de servicio** (IAM → Service accounts) con los roles **BigQuery Data Viewer** (sobre el dataset de la exportación) y **BigQuery Job User** (en el proyecto donde corre la consulta). Genera una clave JSON.
4. En Railway pega el JSON (en una línea) en `GOOGLE_BILLING_SA_JSON` y el nombre de la tabla en `GOOGLE_BILLING_BQ_TABLE`.
5. Entra al Scraper y pulsa **Actualizar**.

## Qué esperar
- La exportación **no tiene historial**: solo guarda datos desde el día en que se activa.
- Los datos llegan con **horas de retraso** (a veces hasta ~1 día). Por eso el límite usa el mayor entre el gasto real y el estimado por el contador interno, más los scrapes en curso.
- Hasta que lleguen las primeras filas verás «Sin datos de facturación todavía».
- La cuenta de facturación debe estar en **USD** (las filas en otra moneda se ignoran y se avisa en el estado del sync).
- Sync automático diario (tarea asyncio al arrancar; no corre si ya se sincronizó hace menos de 20 h) + botón manual.

## Actualizar precios
Edita **solo** `backend/services/google_pricing.py` (`SKUS` y `PRICES_AS_OF`). Fuente: https://developers.google.com/maps/billing-and-pricing/pricing

## Qué SKU usa el scraper hoy
La máscara de campos de `google_places_service.py` pide `nationalPhoneNumber` y `websiteUri` (campos Enterprise) → **Places API Text Search Enterprise** (1,000 gratis/mes, $35 por 1,000). El scraper no llama a Place Details. Quitar teléfono y sitio web lo bajaría a Text Search Pro (5,000 gratis, $32 por 1,000), pero el sitio web alimenta la búsqueda de emails.

Fuera del scraper, cada vez que se carga la foto de un lead (`/api/leads/{id}/photo`) se cobra una llamada **Places API Place Details Photos** (1,000 gratis/mes, $7 por 1,000). La foto no se guarda, así que abrir el mismo lead dos veces cuenta dos llamadas.
