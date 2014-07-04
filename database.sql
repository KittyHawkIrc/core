create table op (
    username text
);

create table command (
    name text unique,
    response text
);

create table seen (
    nick text unique,
    date text
);
