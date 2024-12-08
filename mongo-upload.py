from pymongo import MongoClient

# MongoDB connection string and database details
mongo_uri = 'mongodb://admin:pass@localhost:27017/'
db_name = 'jenkins-data'
collection_name = 'build_data'


# Using a context manager to ensure the client is closed properly
with MongoClient(mongo_uri) as client:
    # Access the specified database
    db = client[db_name]
    
    # Access the specified collection (creates it if it doesn't exist)
    collection = db[collection_name]
    
    # Generate and insert sample data
    # sample_data = generate_sample_data(10)  # Generate 10 sample records
    result = collection.insert_many(sample_data2)
    
    # Print the result
    print(f"Inserted {len(result.inserted_ids)} documents into '{collection_name}' collection.")
    
    # Verify the insertion
    print("Inserted documents:")
    for user in collection.find():
        print(user)
