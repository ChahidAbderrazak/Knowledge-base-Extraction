CREATE TABLE IF NOT EXISTS evaluation.eval_requests (
    sample_id STRING,
    project_name STRING,
    contact_email STRING,
    input_text STRING,
    output_dict JSON,
    destination_bq_table STRING,
    status STRING,
    locked_by STRING,
    lock_time TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluation.eval_results (
    sample_id STRING,
    evaluation_scores JSON,
    evaluation_justification STRING,
    created_at TIMESTAMP
);
