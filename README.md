# DB-GPT
A Open Database-GPT Experiment, A fully localized project.

![GitHub Repo stars](https://img.shields.io/github/stars/csunny/db-gpt?style=social)

A database-related GPT experimental project, with models and data fully localized for deployment, ensuring absolute privacy and security of data. At the same time, this GPT project can be directly connected to a private database for local deployment, processing private data.

[DB-GPT](https://github.com/csunny/DB-GPT) is an experimental open-source application based on [FastChat](https://github.com/lm-sys/FastChat) and uses [vicuna-13b](https://huggingface.co/Tribbiani/vicuna-13b) as the base model. In addition, this application combines [langchain](https://github.com/hwchase17/langchain) and [llama-index](https://github.com/jerryjliu/llama_index) for [In-Context Learning](https://arxiv.org/abs/2301.00234) based on existing knowledge bases to enhance its database-related knowledge. It can perform tasks such as SQL generation, SQL diagnosis, and database knowledge Q&A.

## Project Scheme
<img src="https://github.com/csunny/DB-GPT/blob/main/asserts/pilot.png" width="600" margin-left="auto" margin-right="auto" >

[DB-GPT](https://github.com/csunny/DB-GPT) is an experimental open-source application that builds upon the [FastChat](https://github.com/lm-sys/FastChat) model and uses vicuna as its base model. Additionally, it looks like this application incorporates langchain and llama-index embedding knowledge to improve Database-QA capabilities. 

Overall, it appears to be a sophisticated and innovative tool for working with databases. If you have any specific questions about how to use or implement DB-GPT in your work, please let me know and I'll do my best to assist you.

## Demo of Running Effects
Run on an RTX 4090 GPU (The origin mov not sped up!, [YouTube](https://www.youtube.com/watch?v=1PWI6F89LPo))
- Running demo

![](https://github.com/csunny/DB-GPT/blob/main/asserts/演示.gif)


- SQL Generation Example
First, select the corresponding database, and then the model can generate SQL based on the corresponding database schema information

<img src="https://github.com/csunny/DB-GPT/blob/main/asserts/SQLGEN.png" width="600" margin-left="auto" margin-right="auto" >

The Generated SQL is runable.

<img src="https://github.com/csunny/DB-GPT/blob/main/asserts/exeable.png" width="600" margin-left="auto" margin-right="auto" >

- Database QA Example 

<img src="https://github.com/csunny/DB-GPT/blob/main/asserts/DB_QA.png" margin-left="auto" margin-right="auto" width="600">

Based on default built-in knowledge base QA

<img src="https://github.com/csunny/DB-GPT/blob/main/asserts/VectorDBQA.png" width="600" margin-left="auto" margin-right="auto" >

# Dependencies
1. First you need to install python requirements.
```
python>=3.9
pip install -r requirements.txt
```
or if you use conda envirenment, you can use this command
```
cd DB-GPT
conda env create -f environment.yml
```

2. MySQL Install

In this project examples, we connect mysql and run SQL-Generate. so you need install mysql local for test. recommand docker
```
docker run --name=mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=aa123456 -dit mysql:latest
```
The password just for test, you can change this if necessary

# Install
1. Base model download
Regarding the base model, you can synthesize according to the [vicuna](https://github.com/lm-sys/FastChat/blob/main/README.md#model-weights)synthesis tutorial.
If you have difficulty with this step, you can also use the model on [Hugging Face](https://huggingface.co/) as a substitute. [Alternative model](https://huggingface.co/Tribbiani/vicuna-7b)

2. Run model server
```
cd pilot/server
python vicuna_server.py
```

3. Run gradio webui
```
python webserver.py 
```

# Featurs
- SQL-Generate
- Database-QA Based Knowledge 
- SQL-diagnosis

In summary, it is a complex and innovative AI tool for databases. If you have any specific questions about how to use or implement DB-GPT in your work, please contact me, I will do my best to provide help. At the same time, everyone is welcome to participate in the project construction and do some interesting things.

# Contribute
[Contribute](https://github.com/csunny/DB-GPT/blob/main/CONTRIBUTING)
# Licence
[MIT](https://github.com/csunny/DB-GPT/blob/main/LICENSE)
