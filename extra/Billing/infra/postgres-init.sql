-- Usuário da aplicação: recebe só as permissões concedidas pelas migrations.
CREATE ROLE nbb_app LOGIN PASSWORD 'app';
CREATE DATABASE nbb_test OWNER nbb_owner;
