#!/usr/bin/python3

from fastapi import FastAPI, HTTPException
from opentelemetry import trace
# from opentelemetry.sdk.metrics.export import ConsoleMetricsExporter # Ezt már nem kell importálni, ha nem használjuk
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# Új import a metrikákhoz
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor
# Új import a metrikákhoz
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

app = FastAPI()

# --- TRACE KONFIGURÁCIÓ ---
# Az OpenTelemetry Trace Provider beállítása
trace.set_tracer_provider(TracerProvider(resource=Resource.create({"service.name": "Order Service"})))
tracer = trace.get_tracer(__name__)

# OTLP Trace Exportőr beállítása
# Az endpoint most az Appserveren futó Alloy OTLP gRPC receiver-ére mutat (általában 4317)
# Feltételezve, hogy az Alloy ugyanazon a gépen fut, mint az app, "localhost" használható.
# Ha más IP-címen fut az Alloy az appserveren belül, akkor azt az IP-t kell ide írni.
span_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
span_processor = BatchExportSpanProcessor(span_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# --- METRIKA KONFIGURÁCIÓ ---
# Az OpenTelemetry Meter Provider beállítása metrikákhoz
meter_provider = MeterProvider(resource=Resource.create({"service.name": "Order Service"}))
meter = meter_provider.get_meter(__name__)
counter = meter.create_counter(name="otel_order", description="Count of orders")

# Új: OTLP Metrika Exportőr beállítása
# Ugyancsak az Appserveren futó Alloy OTLP gRPC receiver-ére mutat (általában 4317)
metric_exporter = OTLPMetricExporter(endpoint="http://localhost:4317")
# Metrika olvasó, ami periodikusan exportálja a metrikákat
metric_reader = PeriodicExportingMetricReader(metric_exporter)
meter_provider.add_metric_reader(metric_reader)


@app.get('/')
async def read_root():
    # Kezdeményez egy trace-t (span-t) a "Connecting to DB" néven
    with tracer.start_as_current_span("Connetcting to DB") as span: # Hozzáadtam a `as span` részt a könnyebb kezeléshez
        try:
            # Szimulálja az adatbázis kapcsolatot
            # Attribútumok beállítása a span-en
            span.set_attribute("db-name", "prod-sql")
            span.set_attribute("connection-status", "success")
            span.set_attribute("Query result count", "1")
            span.set_status(trace.Status.OK) # Sikerre állítja a span státuszát
        except Exception as e:
            # Kivételek kezelése
            span.set_status(trace.Status.ERROR) # Hibára állítja a span státuszát
            span.record_exception(e) # Rögzíti a kivételt
            print(e)
    # Inkementálja az "otel_order" számlálót minden híváskor
    counter.add(1)
    return {"message": "OK"}

if __name__ == "__main__":
    # Instrumentálja a FastAPI alkalmazást, hogy automatikusan generáljon span-eket a HTTP kérésekhez
    FastAPIInstrumentor.instrument_app(app)

    # A FastAPI alkalmazás futtatása az Uvicorn-nal
    # host="0.0.0.0" azért van, hogy minden IP címről elérhető legyen a szerveren
    # port=8000 a HTTP port, amit az alkalmazás figyel
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Ez egy Python-alapú FastAPI alkalmazás, amely:
# egyetlen HTTP végpontot biztosít (/)
# OpenTelemetry-vel metrikákat (otel_order) és trace-eket gyűjt
# OTLP protokollon keresztül trace-et és metrikát küld egy OpenTelemetry collector-nak (ebben az esetben az Appserveren futó Grafana Alloy-nak)
# cél: megfigyelhető web API szimulálása

# Linuxon Python 3 telepítése (ha még nincs):
# sudo apt update
# sudo apt install python3 python3-pip -y

# Szükséges Python csomagok telepítése:
# pip install fastapi uvicorn opentelemetry-sdk opentelemetry-exporter-otlp opentelemetry-instrumentation-fastapi
# vagy
# pip3 install fastapi uvicorn opentelemetry-sdk opentelemetry-exporter-otlp opentelemetry-instrumentation-fastapi

# Ellenőrizd a python3-pip telepítését:
# apt show python3-pip

# Keresd meg a pip3 binárisát:
# which pip3

# Tedd futtathatóvá a fájlt:
# chmod +x metric-tracer.py vagy chmod 700 metric-tracer.py

# Futtatás:
# ./metric-tracer.py
