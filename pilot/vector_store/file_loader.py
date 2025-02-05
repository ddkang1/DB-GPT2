#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import copy
from typing import Optional, List, Dict
from langchain.prompts import PromptTemplate
from langchain.vectorstores import Chroma 
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders import UnstructuredFileLoader, UnstructuredPDFLoader, TextLoader
from langchain.chains import VectorDBQA
from langchain.embeddings import HuggingFaceEmbeddings
from pilot.configs.model_config import VECTORE_PATH, DATASETS_DIR, LLM_MODEL_CONFIG, VECTOR_SEARCH_TOP_K


class KnownLedge2Vector:

    """KnownLedge2Vector class is order to load document to vector 
    and persist to vector store.
        
        Args: 
           - model_name

        Usage:
            k2v = KnownLedge2Vector()
            persist_dir = os.path.join(VECTORE_PATH, ".vectordb") 
            print(persist_dir)
            for s, dc in k2v.query("what is oceanbase?"):
                print(s, dc.page_content, dc.metadata)

    """
    embeddings: object = None 
    model_name = LLM_MODEL_CONFIG["sentence-transforms"]
    top_k: int = VECTOR_SEARCH_TOP_K

    def __init__(self, model_name=None) -> None:
        if not model_name:
            # use default embedding model
            self.embeddings = HuggingFaceEmbeddings(model_name=self.model_name) 
        
    def init_vector_store(self):
        persist_dir = os.path.join(VECTORE_PATH, ".vectordb")
        print("Vector database persistence address: ", persist_dir)
        if os.path.exists(persist_dir):
            # Load from local persistent file
            print("Loading data from local vector...")
            vector_store = Chroma(persist_directory=persist_dir, embedding_function=self.embeddings)
            # vector_store.add_documents(documents=documents)
        else:
            documents = self.load_knownlege()
            # Reinitialize
            vector_store = Chroma.from_documents(documents=documents, 
                                                 embedding=self.embeddings,
                                                 persist_directory=persist_dir)
            vector_store.persist()
        return vector_store 

    def load_knownlege(self):
        docments = []
        for root, _, files in os.walk(DATASETS_DIR, topdown=False):
            for file in files:
                filename = os.path.join(root, file)
                docs = self._load_file(filename)
                # Update metadata
                new_docs = [] 
                for doc in docs:
                    doc.metadata = {"source": doc.metadata["source"].replace(DATASETS_DIR, "")} 
                    print("Document to vector initialization in progress, please wait...", doc.metadata)
                    new_docs.append(doc)
                docments += new_docs
        return docments

    def _load_file(self, filename):
        # Load file
        if filename.lower().endswith(".pdf"):
            loader = UnstructuredFileLoader(filename) 
            text_splitor = CharacterTextSplitter()
            docs = loader.load_and_split(text_splitor)
        else:
            loader = UnstructuredFileLoader(filename, mode="elements")
            text_splitor = CharacterTextSplitter()
            docs = loader.load_and_split(text_splitor)
        return docs

    def _load_from_url(self, url):
        """Load data from url address"""
        pass

    
    def query(self, q):
        """Query similar doc from Vector """
        vector_store = self.init_vector_store()
        docs = vector_store.similarity_search_with_score(q, k=self.top_k)
        for doc in docs:
            dc, s = doc
            yield s, dc

            