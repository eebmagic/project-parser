from chromadb import Documents, EmbeddingFunction, Embeddings
from transformers import AutoModel, AutoTokenizer
import torch
from tqdm import tqdm

class CodetEmbedding(EmbeddingFunction[Documents]):
    def __init__(self):
        self.modelName = 'Salesforce/codet5p-110m-embedding'
        self.model = AutoModel.from_pretrained(self.modelName, trust_remote_code=True)
        self.tokenizer = AutoTokenizer.from_pretrained(self.modelName, trust_remote_code=True)

        self.chunk_size = 10

    def __call__(self, input: Documents) -> Embeddings:
        print(f"MAKING EMBED CALL FOR {len(input)} DOCS")

        # No chunking
        if len(input) < self.chunk_size:
            inputs = self.tokenizer(input, padding=True, truncation=True, return_tensors="pt")
            with torch.no_grad():
                outputs = self.model(**inputs)

            return outputs.tolist()
        
        # With chunking
        else:
            output = []
            print(f"Processing chunked embeddings...")
            for i in tqdm(range(0, len(input), self.chunk_size)):
                chunk = input[i:i+self.chunk_size]
                inputs = self.tokenizer(chunk, padding=True, truncation=True, return_tensors="pt")
                with torch.no_grad():
                    outputs = self.model(**inputs)

                output.extend(outputs.tolist())

            return output
