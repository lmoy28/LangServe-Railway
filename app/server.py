#!/usr/bin/env python
"""A more complex example that shows how to configure index name at run time."""
from typing import Any, Iterable, List, Optional, Type
from dotenv import load_dotenv
from fastapi import FastAPI
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from langchain.schema.embeddings import Embeddings
from langchain.schema.retriever import BaseRetriever
from langchain.schema.runnable import (
    ConfigurableFieldSingleOption,
    RunnableConfig,
    RunnableSerializable,
)
from langchain.schema.vectorstore import VST
from langchain.vectorstores import FAISS, VectorStore, Pinecone
from pinecone import Pinecone as PineconeClient
import os
from langserve import add_routes
from langserve.pydantic_v1 import BaseModel, Field

load_dotenv()

# Define your embeddings
# You need to make sure OpenAIEmbeddings and Pinecone classes are imported or defined in your code
embeddings = OpenAIEmbeddings(openai_api_key=os.environ['OPENAI_API_KEY'])

index_name = 'talkwithpdfnew'

namespace_upsert = '6'  
Document_ID = '474'
filter_criteria = {'reference': Document_ID}

pc=PineconeClient(api_key='8ae669e8-205b-46c5-8e99-344d952de6f4')

pinecone_index_obj= pc.Index(index_name)

# Create the Pinecone instance
vectorstore1 = Pinecone(index=pinecone_index_obj, embedding=embeddings, text_key='text', namespace=namespace_upsert)

vectorstore2 = FAISS.from_texts(["x_n+1=a * xn * (1-xn)"], embedding=OpenAIEmbeddings())


app = FastAPI(
    title="LangChain Server",
    version="1.0",
    description="Spin up a simple api server using Langchain's Runnable interfaces",
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/jp")
def coucou():
    return {"JP": "is a squirrel", "status": "casse noisette"}


class UnderlyingVectorStore(VectorStore):
    """This is a fake vectorstore for demo purposes."""

    def __init__(self, collection_name: str) -> None:
        """Fake vectorstore that has a collection name."""
        self.collection_name = collection_name

    def as_retriever(self) -> BaseRetriever:
        if self.collection_name == "index1":
            return vectorstore1.as_retriever()
        elif self.collection_name == "index2":
            return vectorstore2.as_retriever()
        else:
            raise NotImplementedError(
                f"No retriever for collection {self.collection_name}"
            )

    def add_texts(
        self,
        texts: Iterable[str],
        metadatas: Optional[List[dict]] = None,
        **kwargs: Any,
    ) -> List[str]:
        raise NotImplementedError()

    @classmethod
    def from_texts(
        cls: Type[VST],
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        **kwargs: Any,
    ) -> VST:
        raise NotImplementedError()

    def similarity_search(
        self, embedding: List[float], k: int = 4, **kwargs: Any
    ) -> List[Document]:
        raise NotImplementedError()


class ConfigurableRetriever(RunnableSerializable[str, List[Document]]):
    """Create a custom retriever that can be configured by the user.

    This is an example of how to create a custom runnable that can be configured
    to use a different collection name at run time.

    Configuration involves instantiating a VectorStore with a collection name.
    at run time, so the underlying vectorstore should be *cheap* to instantiate.

    For example, it should not be making any network requests at instantiation time.

    Make sure that the vectorstore you use meets this criteria.
    """

    collection_name: str

    def invoke(
        self, input: str, config: Optional[RunnableConfig] = None
    ) -> List[Document]:
        """Invoke the retriever."""
        vectorstore = UnderlyingVectorStore(self.collection_name)
        retriever = vectorstore.as_retriever()
        return retriever.invoke(input, config=config)


configurable_collection_name = ConfigurableRetriever(
    collection_name="index1"
).configurable_fields(
    collection_name=ConfigurableFieldSingleOption(
        id="collection_name",
        name="Retrievers",
        description="The name of the collection to use for the retriever.",
        options={
            "Basic Retriever": "index1",
            "Index 2": "index2",
        },
        default="Basic Retriever",
    )
)


class Request(BaseModel):
    __root__: str = Field(default="cat", description="Search query")

add_routes(app, configurable_collection_name.with_types(input_type=Request))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)