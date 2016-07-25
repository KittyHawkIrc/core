create table op (
    username text
);

create table command (
    name text unique,
    response text
);

create table profile (
    nickname text unique,
    ident text,
    hostmask text unique,
    loc_lat float,
    loc_lng float,
    unit integer,
    gender integer,
    height float,
    weight float,
    privacy integer,
    isverified integer,
    isop integer
);
