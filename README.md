# Backend

The backend will be a Flask Python API around the Python bindings for the Moira C API.

This could also be a general-purpose API around Moira calls (not necessarily mailing-list related ones), so it should outgrow this repo soon enough.

# Webathena authentication

All requests must be authenticated. There are two ways to do this:

* `Authorization: webathena [base64-encoded JSON]` header
* `webathena` GET parameter (also base64-encoded JSON)

# HTTP API documentation

## Test that authentication is working

`GET /test`

Shows the kerberos tickets you passed to the server, or otherwise shows you whether authentication worked. Designed only to be tested by a human. Clients should use `GET /users/me` instead.

## Users (related to moira lists)

### Get info about user

`GET /users/{user}`

`GET /users/me`

If `me` is used in place of `{user}`, it means the person who's authenticated to the API

No input taken.

Returns:

```json
{
    "name": string,
    "mit_id": int,
    "class_year": string,
    "department": string,
}
```

Errors:

* 404: user not found
* 403: permission denied (if you try to query someone other than yourself)

### Get everything this user can administer

`GET /users/{name}/belongings`

With normal Moira privileges, `{name}` can only be your own username or the special keyword "me".

Output:

```json
[
    {
        "type": "list" | "machine" | "filesys" | ... ,
        "name": string,
    },
]
```

The non-list types are not well-documented by Moira itself (that I can find at the moment), so expect any arbitrary strings that Moira may return.

Errors:

* 404: user not found
* 403: permission denied (if you try to query someone other than yourself)

### Get lists this user is in

`GET /users/{name}/lists`

Get parameters:

* `include_properties`: bool. Whether to return properties of the mailing list apart from just the names

Output:

If `include_properties` is `false`, returns an array of strings representing the list names.

If `include_properties` is `true`, returns an array of list objects:

```json
{
    "name": string, // name of the list
    "active": bool, // whether the list is active
    "public": bool, // whether the list is public (i.e. anyone can add themselves to it)
    "hidden": bool, // whether the list is hidden (i.e. only admins can know who is in it)
    "is_mailing_list": bool, // whether the list should forward mail to its members
    "is_afs_group": bool, // whether the list membership should be able to have definable permissions on AFS (and membership accessable through scripts via AFS-specific commands)
}
```

Errors:

* 404: user not found
* 403: permission denied (if you try to query someone other than yourself)

### Get tap access user is in

`GET /users/{name}/tapaccess`

```
$ qy _help gplm

   get_pacs_lists_of_member, gplm (member_type, member_name) => list_name, active, publicflg, hidden, maillist, grouplist
```

## Moira Lists

Some info on list properties: http://kb.mit.edu/confluence/display/istcontrib/Moira+List+Settings+Legend#the_group

### Get all (public) lists (by filter)

`GET /lists/`

GET parameters:

* `active`: Must be either `true`, `false`, or `dontcare`. Default `true`.
* `public`: Must be `true`. Default `true`.
* `hidden`: Must be `false`. Default `false`.
* `is_mailing_list`: Must be either `true`, `false`, or `dontcare`. Default `true`.
* `is_afs_group`: Must be either `true`, `false`, or `dontcare`. Default `dontcare`.

Response:

Array of strings representing the list names

### Get a list

`GET /lists/{name}`

Gets the property of a specific list.

Output:

```json
{
    "name": string, // name of the list
    "description": string, // description of the list
    "active": bool, // whether the list is active
    "public": bool, // whether the list is public (i.e. anyone can add themselves to it)
    "hidden": bool, // whether the list is hidden (i.e. only admins can know who is in it)
    "is_mailing_list": bool, // whether the list should forward mail to its members
    "is_afs_group": bool, // whether the list membership should be able to have definable permissions on AFS (and membership accessable through scripts via AFS-specific commands)
    "is_nfs_group": bool, // whether the list membership should be able to have definable permissions on NFS
    "is_physical_access": bool, // whether the list is linked to physical access control
    "is_mailman_list": bool, // whether the list is a mailman list
    "owner": {
        "type": "user" | "list", // is this list owned by a user or a list?
        "name": string, // who owns this list?
    },
    "membership_administrator": null | dict, // like above, but may be null...
    "last_modified": {
        "time": string, // last modified (TODO: use an actual timestamp)
        "user": string, // who modified this list last?
        "tool": string, // what did they use to modify it?
    },
}
```

Errors:

* 404: list does not exist
* 403: permission denied (list is hidden and you do not own it and are not in it)

### Make a list

`POST /lists/`

TODO: this may not actually be even possible (user-facing Moira clients have no option to make a list and `qy` returns `unknown machine`)

Input:

* `add_me`: bool. Whether to add creator to the list (default `true`). Changing this value is discouraged, since creators may end up wondering where all their mail went if `false`.
* TODO: define

### Update a list

`PUT /lists/{name}`

TODO: write

Errors:

* 404: list does not exist
* 403: permission denied (list is hidden and you do not own it)

### Delete a list

`DELETE /lists/{name}`

TODO: write

Errors:

* 404: list does not exist
* 403: permission denied (list is hidden and you do not own it)

### Get members of list

`GET /lists/{name}/members`

Output:

```json
{
    "users": [
        // list of users in the mailing list
    ],
    "lists": [
        // list of lists in the mailing list
        // Clients may choose to recursively or interactively query the members of the list
    ],
    "emails": [
        // list of email addresses in the mailing list
    ],
    "kerberos": [
        // list of kerberos principals in the mailing list
    ],
}
```

Errors:

* 404: list does not exist
* 403: permission denied (list is hidden and you do not own it)

### Add a member to a list

`POST /lists/{name}/members`

Input:

* `type`: Can only be "user", "email", "list", or in rare cases, "kerberos".
* `name`: Who to add to the list

`PUT /lists/{name}/members/me` should be an alias to add yourself (`type` is `user` and `name` is your own username)

Errors:

* 201: added successfully
* 404: list does not exist
* 403: permission denied

Add a member to a mailing list. You can only add people to the mailing list if you are an owner or membership administrator, or if the list is public and you want to add yourself.

### Get everything this list can administer

`GET /lists/{name}/belongings`

See documentation for `GET /users/{name}/belongings` -- same output

### Get lists this list is in

`GET /lists/{name}/lists`

See documentation for `GET /users/{name}/lists` -- same input and output

### Remove a member from a list

`DELETE /lists/{name}/members/{member}?type={type}`

Alternatively, `type` can be in the request body instead of the query URL.

Errors:

* 200: successfully deleted
* 404: list does not exist
* 403: permission denied (not self or membership administrator)
* 400: invalid input - for instance, tried to delete someone who is not in the list anyway

### Get administrator of the list

`GET /lists/{name}/owner`

NOTE: you should not need this query, because `GET /lists/{name}` already returns this

### Set administrator of the list

`PUT /lists/{name}/owner`

TODO: write

### Get membership administrator of the list

`GET /lists/{name}/membership_admin`

NOTE: you should not need this query, because `GET /lists/{name}` already returns this

### Set membership administrator of the list

`PUT /lists/{name}/membership_admin`

`POST /lists/{name}/membership_admin` (only if no membership admin)

TODO: write

### Delete membership administrator of the list

`DELETE /lists/{name}/membership_admin`

TODO: write

## PO Boxes (i.e. mail forwarding)

TODO: define spec and implement

## Finger

TODO: define spec and implement
