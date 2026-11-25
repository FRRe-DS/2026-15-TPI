"""SDK opcional: sin inicialización durante migraciones ni cambios en el dominio."""

from atexit import register
from os import getenv

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.api.observabilidad import InicioSolicitud

_configurado = False


def instrumentar(app: FastAPI) -> None:
    global _configurado
    if not _configurado:
        resource = Resource.create(
            {
                "service.name": getenv("OTEL_SERVICE_NAME", "m3-conductores-grupo15"),
                "service.namespace": "utn-frre",
                "deployment.environment.name": "local",
            }
        )
        trazas = TracerProvider(resource=resource)
        trazas.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        metricas = MeterProvider(
            resource=resource,
            metric_readers=[
                PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=30000)
            ],
            views=[
                View(
                    instrument_name="m3.driver.*.duration",
                    aggregation=ExplicitBucketHistogramAggregation(
                        boundaries=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
                    ),
                )
            ],
        )
        trace.set_tracer_provider(trazas)
        metrics.set_meter_provider(metricas)
        PsycopgInstrumentor().instrument(tracer_provider=trazas, meter_provider=metricas)
        SystemMetricsInstrumentor(
            config={
                "process.cpu.time": ["user", "system"],
                "process.cpu.utilization": None,
                "process.memory.usage": None,
            }
        ).instrument(meter_provider=metricas)
        register(trazas.shutdown)
        register(metricas.shutdown)
        _configurado = True
    app.add_middleware(InicioSolicitud)
    FastAPIInstrumentor.instrument_app(app)
