OceanBase Database is a fully self-developed enterprise-level native distributed database that achieves financial-grade high availability on ordinary hardware. It pioneers the "three-zone, five-center" city-level fault-tolerant automatic disaster recovery new standard, refreshing the TPC-C benchmark test with a single cluster scale exceeding 1500 nodes, featuring cloud-native, strong consistency, and high compatibility with Oracle/MySQL.

Core Features
High Availability
The original "three-zone, five-center" disaster recovery architecture solution establishes a new non-destructive disaster recovery standard for the financial industry. It supports same-city/different-city disaster recovery, multi-location and multi-active, meeting the financial industry's 6-level disaster recovery standard (RPO=0, RTO<8s), with zero data loss.
High Compatibility
Highly compatible with Oracle and MySQL, covering most common functions, supporting procedural languages, triggers, and other advanced features. It provides automatic migration tools, supports migration evaluation and reverse synchronization to ensure data migration security, and can support the replacement of critical industry core scenarios such as finance, government, and operators.
Horizontal Scaling
Transparent horizontal scaling is achieved, supporting rapid expansion and contraction of business. It also achieves high performance through a near-memory processing architecture. The cluster supports thousands of nodes, with a single cluster's maximum data volume exceeding 3PB and the maximum single table row count reaching trillions.
Low Cost
Based on the LSM-Tree high compression engine, storage costs are reduced by 70%-90%; native support for multi-tenant architecture, the same cluster can provide services for multiple independent businesses, with data isolation between tenants, reducing deployment and operation costs.
Real-time HTAP
Based on "one set of data, one engine," it supports both online real-time transactions and real-time analysis scenarios. Multiple copies of "one set of data" can be stored in various forms for different workloads, fundamentally maintaining data consistency.
Secure and Reliable
12 years of fully independent research and development, code-level controllability, self-developed stand-alone distributed integrated architecture, large-scale financial core scenario reliability verification for 9 years; comprehensive role-based access control system, data storage and communication full link transparent encryption, support for national encryption algorithms, and passed the third-level special compliance test for equal protection.
In-depth understanding of OceanBase Database
You can learn more about the OceanBase Database through the following content:

OceanBase uses general-purpose server hardware, relies on local storage, and the multiple servers used for distributed deployment are also peer-to-peer, with no special hardware requirements. OceanBase's distributed database processing adopts a Shared Nothing architecture, and the SQL execution engine within the database has distributed execution capabilities.

On the server, OceanBase runs a single-process program called observer as the running instance of the database, using local file storage for data and transaction Redo logs.

OceanBase cluster deployment requires configuring availability zones (Zones), composed of several servers. The availability zone is a logical concept, representing a group of nodes within the cluster with similar hardware availability, which has different meanings in different deployment modes. For example, when the entire cluster is deployed within the same data center (IDC), the nodes of an availability zone can belong to the same rack, the same switch, etc. When the cluster is distributed across multiple data centers, each availability zone can correspond to a data center.

User-stored data can store multiple copies within the distributed cluster for fault tolerance and disaster recovery, as well as for dispersing read pressure. There is only one copy of the data within an availability zone, and different availability zones can store multiple copies of the same data, with data consistency guaranteed between replicas by consensus protocols.

OceanBase has built-in multi-tenant features, where each tenant is an independent database for users. A tenant can set its distributed deployment method at the tenant level. Tenants are isolated from each other in terms of CPU, memory, and IO.

OceanBase's database instances internally consist of different components working together. These components are arranged from the bottom up, consisting of storage layer, replication layer, balance layer, transaction layer, SQL layer, and access layer.

Storage layer
The storage layer provides data storage and access at the granularity of a table or a partition. Each partition corresponds to a Tablet (shard) used for storing data, and non-partitioned user-defined tables also correspond to a Tablet.

The internal structure of a Tablet is a layered storage structure, with a total of 4 layers. DML operations such as insertions, updates, and deletions are first written to MemTable. When MemTable reaches a certain size, it is dumped to disk as an L0 SSTable. When the number of L0 SSTables reaches the threshold, multiple L0 SSTables are merged into an L1 SSTable. During the configured business off-peak hours every day, the system merges all MemTables, L0 SSTables, and L1 SSTables into a Major SSTable.

Each SSTable internally has 2MB fixed-length macro blocks as the basic unit, and each macro block consists of multiple variable-length micro blocks.

During the merging process, Major SSTable's micro blocks are converted to a different format using encoding. The data within the micro blocks is encoded column-wise, with encoding rules including dictionary/run-length/constant/delta encoding. After each column is compressed, further inter-column equal value/substring encoding is performed. Encoding can greatly compress data and refine column-level feature information to further accelerate subsequent query speeds.

After encoding compression, lossless compression can be further applied according to the user-specified general compression algorithm, further improving data compression ratio.

Replication layer
The replication layer uses log streams (LS, Log Stream) to synchronize the state among multiple replicas. Each Tablet corresponds to a specific log stream, and Redo logs generated by DML operations written to a Tablet's data are persisted in the log stream. Multiple replicas of a log stream are distributed across different availability zones, and these replicas maintain a consensus algorithm, with one replica chosen as the primary replica and the others as secondary replicas. DML and strongly consistent queries of a Tablet are performed only on the primary replica of the corresponding log stream.

Usually, each tenant will have only one primary replica of a log stream on each machine, and there may be multiple secondary replicas of other log streams. The total number of log streams for a tenant depends on the configuration of Primary Zone and Locality.

Log streams use a custom Paxos protocol to persist Redo logs on the local server, and send them to secondary replicas of the log stream via the network. Secondary replicas respond to the primary replica after completing their own persistence. The primary replica confirms the successful persistence of the corresponding Redo logs after verifying that a majority of replicas have persisted successfully. Secondary replicas use the contents of Redo logs to replay in real-time, ensuring their state is consistent with the primary replica.

After being elected as the primary replica, the log stream's primary replica obtains a lease (Lease). The primary replica in normal operation will continuously extend the lease term through the election protocol during the lease's validity period. The primary replica will only perform primary work while the lease is valid, and the lease mechanism ensures the database's ability to handle exceptions.

The replication layer can automatically cope with server failures, ensuring the continuous availability of database services. If there are issues with less than half of the secondary replica servers, the database service is not affected because more than half of the replicas are still working normally. If the primary replica server has a problem, its lease will not be renewed. After the lease expires, other secondary replicas will elect a new primary replica through the election protocol and grant a new lease, after which the database service can be restored.

Balance layer
When creating a new table or adding a new partition, the system selects an appropriate log stream to create a Tablet based on the balance principle. When the tenant's properties change, new machine resources are added, or after a long period of use, Tablets become unbalanced across the machines. The balance layer balances data and services among multiple servers again through log stream splitting and merging operations and, during this process, collaborates with the movement of log stream replicas.

When a tenant expands, obtaining more server resources, the balance layer splits the existing log streams within the tenant, selects an appropriate number of Tablets to split into new log streams, and then migrates the new log streams to the newly added servers to fully utilize the expanded resources. When a tenant shrinks, the balance layer migrates the log streams on the servers to be reduced to other servers and merges them with the existing log streams on other servers to reduce resource usage.

After long-term use of the database, the originally balanced state may be disrupted as tables are continuously created and deleted, and more data is written, even if there is no change in the number of server resources. The most common situation is when users delete a batch of tables, which may have originally been concentrated on some machines, causing a reduced number of Tablets on these machines. Other machines' Tablets should be balanced to these machines with fewer Tablets. The balance layer periodically generates balance plans, splitting temporary log streams from log streams on servers with more Tablets, carrying the Tablets to be moved, and merging the temporary log streams with the target server's log streams to achieve a balanced effect.

Transaction layer
The transaction layer ensures the atomicity of single and multiple log stream DML operation submissions and guarantees the multi-version isolation capability between concurrent transactions.

Atomicity
For a transaction's modifications on a log stream, even if it involves multiple Tablets, the write-ahead log of the log stream can ensure the atomicity of the transaction submission. When a transaction's modifications involve multiple log streams, each log stream generates and persists its write-ahead log, and the transaction layer ensures submission atomicity through an optimized two-phase commit protocol.

The transaction layer selects one of the transaction's modified log streams to generate a coordinator state machine. The coordinator communicates with all modified log streams of the transaction to determine if the write-ahead log is persisted. When all log streams have completed persistence, the transaction enters the commit state, and the coordinator drives all log streams to write the transaction's Commit log, indicating the final commit state of the transaction. When secondary replicas replay or the database restarts, committed transactions are determined through Commit logs for each log stream's transaction state.

In the case of a crash-restart scenario, transactions that were not completed before the crash may have written the write-ahead log but not the Commit log. Each log stream's write-ahead log contains a list of all log streams for the transaction, which can be used to re-determine which log stream is the coordinator and restore the coordinator's state, advancing the two-phase state machine again until the transaction reaches the final Commit or Abort state.

Isolation
The GTS service generates continuously increasing timestamps within a tenant, ensuring availability through multiple replicas. The underlying mechanism is the same as the log stream replica synchronization mechanism described in the replication layer above.

Each transaction obtains a timestamp from the GTS when submitting, which serves as the transaction's commit version number and is persisted in the log stream's write-ahead log. All modified data within the transaction is marked with this commit version number.

At the beginning of each statement (for Read Committed isolation level) or each transaction (for Repeatable Read and Serializable isolation levels), a timestamp is obtained from the GTS as the read version number for the statement or transaction. When reading data, data with a transaction version number greater than the read version number is skipped, providing a unified global data snapshot for read operations.

SQL Layer
The SQL layer translates user SQL requests into data access for one or more Tablets.

SQL Layer Components
The execution process of the SQL layer for a request includes: Parser, Resolver, Transformer, Optimizer, Code Generator, and Executor.

Parser is responsible for lexical/syntactic parsing. It breaks down user SQL into "Tokens" and parses the entire request according to predefined grammar rules, converting it into a Syntax Tree.

Resolver is responsible for semantic analysis, translating Tokens in the SQL request into corresponding objects (such as databases, tables, columns, indexes, etc.) based on database metadata. The generated data structure is called a Statement Tree.

Transformer is responsible for logical rewriting, transforming the SQL into an equivalent form based on internal rules or cost models and providing it to the subsequent optimizer for further optimization. The Transformer works by making equivalent transformations on the original Statement Tree, and the result is still a Statement Tree.

Optimizer generates the best execution plan for the SQL request, considering factors such as SQL semantics, object data characteristics, and object physical distribution. It solves problems like access path selection, join order selection, join algorithm selection, and distributed plan generation, ultimately generating the execution plan.

Code Generator converts the execution plan into executable code without making any optimization choices.

Executor initiates the execution process of SQL.

In addition to the standard SQL process, the SQL layer also has Plan Cache capabilities, caching historical execution plans in memory, allowing subsequent executions to reuse the plan and avoid redundant query optimization. With the Fast-parser module, which uses lexical analysis to directly parameterize text strings and obtain parameterized text and constant parameters, SQL can directly hit the Plan Cache, speeding up the execution of frequent SQL.

Multiple Plans
The SQL layer execution plans are divided into local, remote, and distributed plans. Local execution plans only access data on the local server. Remote execution plans only access data on a non-local server. Distributed plans access data on more than one server, and the execution plan is divided into multiple sub-plans that run on multiple servers.

The SQL layer's parallel execution capabilities can break down the execution plan into multiple parts, executed by multiple execution threads, implementing parallel processing of the execution plan through a certain scheduling method. Parallel execution fully utilizes server CPU and IO processing capabilities, shortening the response time of individual queries. Parallel query technology can be applied to distributed execution plans as well as local execution plans.

Access Layer
obproxy is the access layer of OceanBase database, responsible for forwarding user requests to the appropriate OceanBase instance for processing.

obproxy is an independent process instance, separate from OceanBase's database instance deployment. obproxy listens to network ports, is compatible with the MySQL network protocol, and supports applications using MySQL drivers to directly connect to OceanBase.

obproxy can automatically discover the data distribution information of the OceanBase cluster. For each SQL statement of the proxy, it will try to identify the data accessed by the statement and forward the statement directly to the OceanBase instance where the data is located.

obproxy has two deployment methods. One is to deploy on every application server that needs to access the database, and the other is to deploy on the same machine as OceanBase. In the first deployment method, the application directly connects to the obproxy deployed on the same server, and all requests are sent by obproxy to the appropriate OceanBase server. In the second deployment method, a network load balancing service is required to aggregate multiple obproxies into a single entry address to provide services to applications.

OceanBase database adopts a Shared-Nothing architecture, with fully equal nodes. Each node has its own SQL engine, storage engine, and transaction engine, running on a cluster of ordinary PC servers, featuring high scalability, high availability, high performance, low cost, and high compatibility with mainstream databases.

An OceanBase database cluster consists of several nodes. These nodes are divided into several availability zones (Zones), with each node belonging to one availability zone. The availability zone is a logical concept, representing a group of nodes within the cluster with similar hardware availability. It represents different meanings in different deployment modes. For example, when the entire cluster is deployed in the same data center (IDC), the nodes of an availability zone can belong to the same rack, the same switch, etc. When the cluster is distributed across multiple data centers, each availability zone can correspond to a data center. Each availability zone has two attributes, IDC and region (Region), describing the IDC where the availability zone is located and the region to which the IDC belongs. Generally, the region refers to the city where the IDC is located. The IDC and Region attributes of the availability zone need to reflect the actual situation during deployment so that the automatic disaster recovery processing and optimization strategies within the cluster can work better. According to the different high availability requirements of the business for the database system, OceanBase clusters provide a variety of deployment modes. See High Availability Architecture Overview.

In the OceanBase database, the data of a table can be horizontally split into multiple shards according to a certain partitioning rule. Each shard is called a table partition or simply a partition (Partition). A row of data belongs to and only belongs to one partition. The partition rules are specified by the user when creating the table, including hash, range, list, and other types of partitions, as well as support for secondary partitions. For example, the order table in the transaction library can be divided into several primary partitions according to the user ID, and then each primary partition can be divided into several secondary partitions according to the month. For secondary partition tables, each subpartition of the second level is a physical partition, while the first level partition is just a logical concept. Several partitions of a table can be distributed on multiple nodes within an availability zone. Each physical partition has a storage layer object for storing data called Tablet, used to store ordered data records.

When users modify records in a Tablet, in order to ensure data persistence, it is necessary to log redo logs (REDO) to the corresponding log stream (Log Stream) of the Tablet. Each log stream serves multiple Tablets on its node. In order to protect data and not interrupt services when a node fails, each log stream and its associated Tablet have multiple replicas. Generally speaking, multiple replicas are distributed across multiple different availability zones. Among the multiple replicas, there is only one replica that accepts modification operations, called the leader replica (Leader), and other replicas are called follower replicas (Follower). Consistency between replicas is achieved through a distributed consensus protocol based on Multi-Paxos between the leader and follower replicas. When the node where the leader replica is located fails, a follower replica will be elected as the new leader replica and continue to provide services.

An observer service process runs on each node in the cluster, containing multiple operating system threads internally. Node functions are all equivalent. Each service is responsible for the storage and retrieval of partitioned data on its node, as well as the parsing and execution of SQL statements routed to the local machine. These service processes communicate with each other through the TCP/IP protocol. At the same time, each service listens for connection requests from external applications, establishes connections and database sessions, and provides database services. For more information on observer service processes, see the thread overview.

In order to simplify the management of deploying multiple business databases on a large scale and reduce resource costs, the OceanBase database provides a unique multi-tenant feature. Within an OceanBase cluster, many isolated database "instances" can be created, called a tenant. From the perspective of an application, each tenant is an independent database. Moreover, each tenant can choose MySQL or Oracle compatibility mode. When an application connects to a MySQL tenant, it can create users and databases under the tenant, with the same usage experience as an independent MySQL library. Similarly, when an application connects to an Oracle tenant, it can create schemas, manage roles, etc., under the tenant, with the same usage experience as an independent Oracle library. After a new cluster is initialized, a special tenant called sys, known as the system tenant, will exist. The system tenant stores the cluster's metadata and is a MySQL-compatible tenant.

To isolate tenant resources, each observer process can have multiple virtual containers belonging to different tenants, called resource units (UNIT). The resource units of each tenant on multiple nodes form a resource pool. Resource units include CPU and memory resources.

In order to shield application programs from the details of internal partitioning and replica distribution, making access to distributed databases as simple as accessing single-machine databases, we provide obproxy proxy services. Application programs do not directly connect to OBServer, but connect to obproxy, which then forwards SQL requests to the appropriate OBServer node. Obproxy is a stateless service, and multiple obproxy nodes provide a unified network address to applications through network load balancing (SLB).

OceanBase database was born with the development of Alibaba's e-commerce business, grew with the development of Ant Group's mobile payment business, and finally broke through and entered the external market after more than a decade of use and polishing in various businesses. This section briefly describes some milestone events in the development process of the OceanBase database.

Birth

In 2010, Dr. Yang Zhenkun, the founder of OceanBase, led the start-up team to launch the OceanBase project. The first application was Taobao's favorites business. Today, favorites are still OceanBase's customers. The single-table data volume of favorites is very large, and OceanBase uses a unique method to solve the high-concurrency large-table-to-small-table connection requirements.

Relational Database

In the early versions, applications accessed the OceanBase database through customized API libraries. In 2012, OceanBase released a version supporting SQL, initially becoming a fully functional general relational database.

First Try in Financial Services

OceanBase entered Alipay (later Ant Group) and began to be applied to financial-grade business scenarios. In the 2014 "Double 11" promotion event, OceanBase started to handle part of the transaction library traffic. Subsequently, the newly established MYbank ran all core transaction libraries on the OceanBase database.

Financial-grade Core Library

In 2016, OceanBase released version 1.0 after redesigning the architecture, supporting distributed transactions, improving scalability in high-concurrency write businesses, and implementing a multi-tenant architecture, which continues to this day. At the same time, by 2016's "Double 11", 100% of Alipay's core library business traffic ran on the OceanBase database, including transactions, payments, memberships, and the most important accounting library.

Entering the External Market

In 2017, OceanBase database began pilot external businesses and successfully applied to Bank of Nanjing.

Commercial Acceleration

In 2018, OceanBase database released version 2.0, starting to support Oracle compatibility mode. This feature reduced application transformation adaptation costs and quickly spread among external customers.

Climbing to the Peak

In 2019, OceanBase database V2.2 participated in the TPC-C evaluation, representing the most authoritative OLTP database, and ranked first in the world with a score of 60 million tpmC. Subsequently, in 2020, it refreshed the record with 700 million tpmC and still ranks first to this day. This fully demonstrates the excellent scalability and stability of the OceanBase database. OceanBase is the first and only Chinese database product on the TPC-C list to date.

HTAP Mixed Load

In 2021, OceanBase database V3.0, based on a new vectorized execution engine, refreshed the evaluation list with a score of 15.26 million QphH in the TPC-H 30000GB evaluation. This marks a fundamental breakthrough in OceanBase's ability to handle AP and TP mixed loads with one engine.

Open Source and Openness

On June 1, 2021, Children's Day, OceanBase database announced full open source, open cooperation, and ecosystem co-construction.

OceanBase database adopts a single-cluster multi-tenant design, naturally supports cloud database architecture, and supports various deployment forms such as public cloud, private cloud, and hybrid cloud.

Architecture

OceanBase database achieves resource isolation through tenants, making each database service instance unaware of the existence of other instances, and ensures tenant data security through access control. Combined with OceanBase's powerful scalability, it can provide secure and flexible DBaaS services.

Tenant is a logical concept. In OceanBase database, tenant is the unit of resource allocation and the foundation for database object management and resource management. It has a significant impact on system operation and maintenance, especially for cloud database operation and maintenance. To some extent, tenant is equivalent to the traditional database concept of "instance." Tenants are completely isolated from each other. In terms of data security, OceanBase database does not allow cross-tenant data access to ensure that users' data assets are not at risk of being stolen by other tenants. In terms of resource usage, OceanBase database appears as a tenant "exclusive" of its resource quota. Overall, the tenant (tenant) is both a container for various types of database objects and a container for resources (CPU, Memory, IO, etc.).

OceanBase database can support both MySQL mode and Oracle mode tenants in one system simultaneously. When creating a tenant, users can choose to create a MySQL compatible mode tenant or an Oracle compatible mode tenant. Once the tenant's compatibility mode is determined, it cannot be changed, and all data types, SQL features, views, etc., are consistent with the MySQL database or Oracle database accordingly.

MySQL Mode
MySQL mode is a tenant type function supported by OceanBase database to reduce the cost of business system transformation caused by migrating MySQL database to OceanBase database. It allows database designers, developers, and administrators to reuse accumulated MySQL database technology knowledge and experience and quickly get started with OceanBase database. OceanBase database's MySQL mode is compatible with most functions and syntax of MySQL 5.7, as well as full compatibility with MySQL 5.7 and partial JSON functions of version 8.0. Applications based on MySQL can be smoothly migrated.

Oracle Mode
OceanBase database has supported Oracle compatibility mode since version V2.x.x. Oracle mode is a tenant type function supported by OceanBase database to reduce the cost of business system transformation caused by migrating Oracle database to OceanBase database. It allows database design developers and administrators to reuse accumulated Oracle database technology knowledge and experience and quickly get started with OceanBase database. Oracle mode currently supports most Oracle syntax and procedural language functions, enabling most Oracle businesses to be automatically migrated with minimal modifications.

OceanBase database is a multi-tenant architecture. In version V4.0.0 and earlier, only two types of tenants were supported: system tenants and user tenants. From version V4.0.0, the concept of Meta tenant was introduced. Therefore, there are currently three types of tenants visible to users: system tenants, user tenants, and Meta tenants.

System Tenant
The system tenant is the default tenant created with the cluster and has the same lifecycle as the cluster. It is responsible for managing the lifecycle of the cluster and all tenants. The system tenant has only one log stream and supports single-point writes without scalability.

System tenants can create user tables, and all user table and system table data are served by log stream 1. System tenant data is private to the cluster and does not support physical synchronization and backup recovery between primary and standby clusters.

User Tenant
User tenants are tenants created by users, providing complete database functionality and supporting both MySQL and Oracle compatibility modes. User tenants support horizontal scalability of service capabilities to multiple machines, support dynamic expansion and contraction, and automatically create and delete log streams based on user configurations.

User tenant data has stronger data protection and availability requirements, supporting cross-cluster physical synchronization and backup recovery. Typical data includes Schema data, user table data, and transaction data.

Meta Tenant
Meta tenant is a tenant that OceanBase database internally manages, and a corresponding Meta tenant is automatically created for each user tenant created by the system, with a consistent life cycle with the user tenant.

Meta tenant is used to store and manage user tenant's cluster private data, which does not require cross-database physical synchronization and physical backup recovery. This data includes: configuration items, location information, replica information, log stream status, backup recovery related information, merge information, etc.

Tenant Comparison
From the user's perspective, the differences between system tenants, user tenants, and Meta tenants are shown in the table below.
OceanBase database is a multi-tenant database system, and a cluster can contain multiple independent tenants, each providing independent database services. In OceanBase database, the concepts of resource configuration (unit_config), resource pool (Resource Pool), and resource unit (Unit) are used to manage the available resources for each tenant.

Before creating a tenant, it is necessary to determine the tenant's resource configuration and resource usage scope. The general process of creating a tenant is as follows:

Resource configuration is the configuration information describing the resource pool, used to describe the specifications of CPU, memory, storage space, and IOPS available for each resource unit in the resource pool. Modifying the resource configuration can dynamically adjust the specifications of the resource unit. It should be noted that the resource configuration specifies the service capability provided by the corresponding resource unit, not the real-time load of the resource unit. The example statement for creating a resource configuration is as follows: