# project-parser

## Usage
1. Clone some projects into the `projects/` dir
2. Run the `main.py` script to index all the project files
3. Run the `Query Notebook.ipynb` jupyter notebook.
   Run a query to 


## About
Uses the [Salesforce codet5p-110m-embedding model](https://huggingface.co/Salesforce/codet5p-110m-embedding)
model to build embeddings.

This model is supposed to work better for aligning natural text queries with code samples
according to [the CodeXGLUE benchmark](https://paperswithcode.com/sota/code-search-on-codexglue-advtest).

