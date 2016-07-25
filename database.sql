create table op (
    username text
);

create table command (
    name text unique,
    response text
);

create table profile (
    uuid text unique,
    username text unique,
    nickname text unique,
    location text,
    gender integer,
    timezone integer,
    unit text,
    privacy integer,
    isverified integer,
    isop integer
);
