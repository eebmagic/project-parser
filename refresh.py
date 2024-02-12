'''
A script to delete the collection 'functions' from the database.
'''
import chromadb

client = chromadb.PersistentClient(path='./db')
print(client.list_collections())

client.delete_collection('functions')
print(client.list_collections())
