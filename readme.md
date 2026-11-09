# Calcolatore di serie

Questa applicazione consiste in un sito Flask per il calcolo di serie matematiche.

Consiste in un front end Flask che usa template Jinja, autenticazione con user/password e due ruoli utente (user e admin).
In aggiunta a ciò viene esposta una API, utilizzabile tramite API-KEY (Authentication Bearer)
Il calcolo delle serie viene fatto tramite un worker separato che consulta una coda di task tramite RabbitMQ, in questo modo è possibile aumentare i worker.
Utenti, ruoli, chiavi e serie sono salvati in DB relazionale sqlite, usando flask_sqlalchemy, flask_migrate. 
L'autenticazione user viene fatta con flask_login, il ruolo controllato tramite decoratore, le routes API controllate tramite decoratore.

