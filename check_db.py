import chromadb

# Connect to the database
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("aerostream_docs")

# Count total documents
count = collection.count()
print(f"Total chunks in database: {count}")

# specific check for Slack
slack_data = collection.get(where={"source": "Slack Thread"})
print(f"Number of Slack threads found: {len(slack_data['ids'])}")