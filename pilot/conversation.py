#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import dataclasses
from enum import auto, Enum
from typing import List, Any
from pilot.configs.model_config import DB_SETTINGS

class SeparatorStyle(Enum):
    
    SINGLE = auto()
    TWO = auto()

@dataclasses.dataclass
class Conversation:
    """This class keeps all conversation history. """

    system: str
    roles: List[str]
    messages: List[List[str]] 
    offset: int
    sep_style: SeparatorStyle = SeparatorStyle.SINGLE
    sep: str = "###"
    sep2: str = None

    # Used for gradio server
    skip_next: bool = False
    conv_id: Any = None

    def get_prompt(self):
        if self.sep_style == SeparatorStyle.SINGLE:
            ret = self.system + self.sep
            for role, message in self.messages:
                if message:
                    ret += role + ": " + message + self.sep  
                else:
                    ret += role + ":"
            return ret

        elif self.sep_style == SeparatorStyle.TWO:
            seps = [self.sep, self.sep2]
            ret = self.system + seps[0]
            for i, (role, message) in enumerate(self.messages):
                if message:
                    ret += role + ":" + message + seps[i % 2]
                else:
                    ret += role + ":"
            return ret

        else:
            raise ValueError(f"Invalid style: {self.sep_style}")
                

    def append_message(self, role, message):
        self.messages.append([role, message])
    
    def to_gradio_chatbot(self):
        ret = []
        for i, (role, msg) in enumerate(self.messages[self.offset:]):
            if i % 2 == 0:
                ret.append([msg, None])
            else:
                ret[-1][-1] = msg

        return ret

    def copy(self):
        return Conversation(
            system=self.system,
            roles=self.roles,
            messages=[[x, y] for x, y in self.messages],
            offset=self.offset,
            sep_style=self.sep_style,
            sep=self.sep,
            sep2=self.sep2,
            conv_id=self.conv_id,
        )

    def dict(self):
        return {
            "system": self.system,
            "roles": self.roles,
            "messages": self.messages,
            "offset": self.offset,
            "sep": self.sep,
            "sep2": self.sep2,
            "conv_id": self.conv_id
        }


def gen_sqlgen_conversation(dbname):
    from pilot.connections.mysql import MySQLOperator
    mo = MySQLOperator(
        **DB_SETTINGS
    )

    message = ""

    schemas = mo.get_schema(dbname)
    for s in schemas:
        message += s["schema_info"] + ";"
    return f"The Schema information of the database {dbname} is as follows: {message}\n"

conv_one_shot = Conversation(
    system="A chat between a curious human and an artificial intelligence assistant, who very familiar with database related knowledge. "
    "The assistant gives helpful, detailed, professional and polite answers to the human's questions. ",
    roles=("Human", "Assistant"),
    messages=(
        (
            "Human",
            "What are the key differences between mysql and postgres?",
        ),
        (
            "Assistant",
            "MySQL and PostgreSQL are both popular open-source relational database management systems (RDBMS) "
            "that have many similarities but also some differences. Here are some key differences: \n"
            "1. Data Types: PostgreSQL has a more extensive set of data types, "
            "including support for array, hstore, JSON, and XML, whereas MySQL has a more limited set.\n"
            "2. ACID compliance: Both MySQL and PostgreSQL support ACID compliance (Atomicity, Consistency, Isolation, Durability), "
            "but PostgreSQL is generally considered to be more strict in enforcing it.\n"
            "3. Replication: MySQL has a built-in replication feature, which allows you to replicate data across multiple servers,"
            "whereas PostgreSQL has a similar feature, but it is not as mature as MySQL's.\n"
            "4. Performance: MySQL is generally considered to be faster and more efficient in handling large datasets, "
            "whereas PostgreSQL is known for its robustness and reliability.\n"
            "5. Licensing: MySQL is licensed under the GPL (General Public License), which means that it is free and open-source software, "
            "whereas PostgreSQL is licensed under the PostgreSQL License, which is also free and open-source but with different terms.\n"

            "Ultimately, the choice between MySQL and PostgreSQL depends on the specific needs and requirements of your application. "
            "Both are excellent database management systems, and choosing the right one "
            "for your project requires careful consideration of your application's requirements, performance needs, and scalability."
        ),
    ),
    offset=2,
    sep_style=SeparatorStyle.SINGLE,
    sep="###"
)
    
conv_vicuna_v1 = Conversation(
    system = "A chat between a curious user and an artificial intelligence assistant. who very familiar with database related knowledge. "
    "The assistant gives helpful, detailed, professional and polite answers to the user's questions. ",
    roles=("USER", "ASSISTANT"),
    messages=(),
    offset=0,
    sep_style=SeparatorStyle.TWO,
    sep=" ",
    sep2="</s>",
)


conv_qa_prompt_template = """ Based on the following known information, provide a professional and detailed answer to the user's question. 
            If you cannot obtain the answer from the provided content, please say: "The content provided in the knowledge base is not sufficient to answer this question", but you can give some suggestions related to the question:

            Known content:
            {context}
            Question:
            {question}
"""

default_conversation = conv_one_shot

conversation_types = {
    "native": "LLM native conversation",
    "default_knownledge": "Default knowledge base conversation",
    "custom":  "New knowledge base conversation",
}

conv_templates = {
    "conv_one_shot": conv_one_shot,
    "vicuna_v1": conv_vicuna_v1,
}


if __name__ == "__main__":
    message = gen_sqlgen_conversation("dbgpt")
    print(message)