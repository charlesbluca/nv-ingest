import logging, time, os, json
from datetime import datetime

from nv_ingest_client.client import NvIngestClient
from nv_ingest_client.primitives import BatchJobSpec
from nv_ingest_client.primitives.tasks import ExtractTask
from nv_ingest_client.primitives.tasks.table_extraction import TableExtractionTask
from nv_ingest_client.primitives.tasks.chart_extraction import ChartExtractionTask
from nv_ingest_client.util.file_processing.extract import extract_file_content


scale = "bo20"
run = 1

logger = logging.getLogger("nv_ingest_client")

t_start = time.time()

client = NvIngestClient(
    message_client_hostname="localhost", # Host where nv-ingest-ms-runtime is running
    message_client_port=36274 # REST port, defaults to 7670
)

def log(msg):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{current_time}: {msg}")

out_dir = f"processed_docs/{run}/{scale}/"
for subdir in ["all", "tables", "text"]:
    os.makedirs(f"{out_dir}/{subdir}", exist_ok=True)

base_dir = f"/raid/charlesb/data/nv-ingest/{scale}/"

job_spec = BatchJobSpec([f"{base_dir}/*.pdf"])
table_data_extract = TableExtractionTask()
chart_data_extract = ChartExtractionTask()
extract_task = ExtractTask(
    document_type="pdf",
    extract_text=True,
    extract_images=True,
    extract_tables=True,
    extract_charts=True
)
job_spec.add_task(extract_task)
job_spec.add_task(table_data_extract)
job_spec.add_task(chart_data_extract)

job_ids = client.add_job(job_spec)
client.submit_job(job_ids, "morpheus_task_queue", batch_size=10)
results = client.fetch_job_result(job_ids, timeout=60, verbose=True)

t_end = time.time()

with open(f"{out_dir}raw_results.json", "w") as fp:
    fp.write(json.dumps(results))

for result in results:
    fn = result[0]["metadata"]["source_metadata"]["source_id"].split("/")[-1]
    texts = []
    tables = []
    for element in result:
        if element['document_type'] == 'text':
            texts.append(element['metadata']['content'])
        elif element['document_type'] == 'structured':
            tables.append(element['metadata']['table_metadata']['table_content'])
    with open(f"{out_dir}/all/{fn}", "w") as fp:
        fp.write(json.dumps(result))
    with open(f"{out_dir}/tables/{fn}", "w") as fp:
        fp.write(json.dumps(tables))
    with open(f"{out_dir}/text/{fn}", "w") as fp:
        fp.write(json.dumps(texts))

now = datetime.now()
dt_hour    = now.strftime("%m-%d-%y_%I")
with open(f"runs/{dt_hour}_batch_extract_time_{scale}_{run}.log", "w") as fp:
    fp.write(str(t_end-t_start) + "," + str(len(results)))
log(f"{scale}: {len(result)} results in {t_end-t_start}")
