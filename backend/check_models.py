from services.ai_service import _get_client

client, model = _get_client("glm")
print("Testing embedding endpoint...")
try:
    resp = client.embeddings.create(
        input=["test text for embeddings"],
        model="cohere.embed-english-v3"
    )
    print("Cohere Embed success! Embedding length:", len(resp.data[0].embedding))
except Exception as e1:
    print("Cohere Embed failed:", e1)
    
    # Try another common embedding model on AWS Bedrock
    try:
        resp = client.embeddings.create(
            input=["test text for embeddings"],
            model="amazon.titan-embed-text-v1"
        )
        print("Titan Embed success! Embedding length:", len(resp.data[0].embedding))
    except Exception as e2:
        print("Titan Embed failed:", e2)
