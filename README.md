# Moira REST API

This is an HTTP API around Moira (and possibly Mailman in the future). 

## Webathena authentication

All requests must be authenticated. There are two ways to do this:

* `Authorization: webathena [base64-encoded JSON]` header
* `webathena` GET parameter (also base64-encoded JSON)

For an example on how to use webathena to get the ticket, see https://github.com/gabrc52/svelte-moira/blob/main/src/lib/webathena.ts

## Changing the app name

If you use this API, your app will be identified as `python3`. If you want to change this,
set the `modby` header to your desired value (Moira has a limit of 8 characters, though).

The app name you choose will show up on WebMoira or any command line utilities under "last modified".

## Errors

If any of the functions returns an error, the output will be the following:

```ts
{
    "code": int | undefined, // error code, only if the error is a moira error
    "name": string | undefined, // short error name
    "description": string, //description of the error
}
```

# HTTP API documentation

## Debugging

### Test that authentication is working

`GET /klist`

Shows the output of `klist`. Clients should use `GET /users/me` instead.

### Who am I?

`GET /whoami`

Simple endpoint to get the kerb of the kerb ticket. ***Do not trust it***: It could have been tampered with from the client side. 

Clients should use `GET /users/me/` instead.

## Ticket validity

`GET /status`

Returns `{ "status": "ok" }` or `{ "status": "expired" }` depending on whether the ticket has expired.

## Raw Moira query

`POST /raw_query/{query}/?arg=a&arg=b`

with parameters `a` and `b` (specify according to your needs)

`GET` works as well.

## Users (related to moira lists)

### Get info about user

`GET /users/{user}/`

`GET /users/me/`

**Note the trailing slash.** 

If `me` is used in place of `{user}`, it means the person who's authenticated to the API

No input taken.

Returns:

```ts
{
    "full_name": string,
    "names": {
        "first": string,
        "middle": string,
        "last": string,
    }
    "kerb": string,
    "mit_id": int,
    "class_year": string,
}
```

Errors:

* 404: user not found
* 403: permission denied (if you try to query someone other than yourself)

### Get everything this user can administer

`GET /users/{name}/belongings`

With normal Moira privileges, `{name}` can only be your own username or the special keyword "me".

Get parameters:

* `recurse`: bool. Default true. Whether to include objects this user can administer because they are in a list that can administer it (and so on), as opposed to a direct ownership.

Output:

```ts
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

* `include_properties`: bool. Defaults to false. Whether to return properties of the mailing list apart from just the names

* `recurse`: bool. Defaults to true. Whether to include the lists a user is in through other lists rather than just directly.

Output:

If `include_properties` is `false`, returns an array of strings representing the list names.

If `include_properties` is `true`, returns an array of list objects:

```ts
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

Returns an array of strings representing the PACS mailing lists

## Moira Lists

Some info on list properties: http://kb.mit.edu/confluence/display/istcontrib/Moira+List+Settings+Legend#the_group

### Get all (public) lists (by filter)

`GET /lists/`

**Note the trailing slash**

GET parameters:

* `active`: Must be either `true`, `false`, or `dontcare`. Default `true`.
* `public`: Must be `true`. Default `true`.
* `hidden`: Must be `false`. Default `false`.
* `is_mailing_list`: Must be either `true`, `false`, or `dontcare`. Default `true`.
* `is_afs_group`: Must be either `true`, `false`, or `dontcare`. Default `dontcare`.
* `confirm`: bool. Whether you actually want to query ten thousand lists. Default `false`

Response:

Array of strings representing the list names

### Get a list

`GET /lists/{name}/`

**Note the trailing slash**

Gets the property of a specific list.

Output:

```ts
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

Output:

The string "success"



### Make a list

`POST /lists/{names}`

TODO: this may not actually be even possible (user-facing Moira clients have no option to make a list and `qy` returns `unknown machine`)

Input:

* `add_me`: bool. Whether to add creator to the list (default `true`). Changing this value is discouraged, since creators may end up wondering where all their mail went if `false`.
* TODO: define

### Update a list

`PATCH /lists/{name}`

Input should be a JSON with any subset of the following parameters:

If they are ommitted or set to null, it means those attributes should not be modified.

Only pass as input those parameters you wish to modify.

* `name`: the new name of the list, if you wish to rename it
* `active`: whether the list is active
* `public`: whether the list is public
* `hidden`: whether the list is hidden
* `is_mailing_list`: whether the list sends mail
* `is_afs_group`: whether the list is a group
* `description`: the new description of the list, if you wish to change it

Other possible parameters (you will likely not need them):

* `is_nfs_group`: whether the list is a NFS group
* `mailman`: whether the list is a mailman list
* `mailman_server`: the mailman server to use (usually MAILMAN.MIT.EDU, but EECS and other departments may have their own). If this is not a mailman list, it should be set to `[NONE]`.
* `is_physical_access`: whether the list is linked to physical access control

Errors:

* 404: list does not exist
* 403: permission denied (list is hidden and you do not own it)

### Delete a list

`DELETE /lists/{name}`

Deletes the given list. The list may not be in use, i.e. it should not have any members and it should not be a member of anything.

Returns the string "success" if successful.

A list may only be deleted if it is not in use as a member
of any other list or as an ACL for an object, and the list itself must be empty.

Errors:

* 404: list does not exist
* 403: permission denied (you do not have permission to delete the list)
* 412: list cannot be deleted because it is in use (MR_IN_USE)

### Get members of list

`GET /lists/{name}/members/`

**Note the trailing slash**

GET parameters:

* `recurse`: Whether to go into the sublists and return their members instead of just a shallow representation. Defaults to false.

Output:

```ts
{
    "users": [
        // list of users in the mailing list
    ],
    "lists": [
        // list of lists in the mailing list
        // Clients may choose to recursively or interactively query the members of the list
    ],
    "emails": [
        // list of email addresses in the mailing list (occasionally includes other strings)
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

`PUT /lists/{name}/members/{user}`

Input (GET parameter):

* `type`: Can only be "user", "email", "list", or in rare cases, "kerberos". Default "user".

`PUT /lists/{name}/members/{me}` should be an alias to add yourself (`type` is `user` and `name` is your own username)

Errors:

* 201: added successfully
* 404: list does not exist
* 403: permission denied
* 409: already in the list

Add a member to a mailing list. You can only add people to the mailing list if you are an owner or membership administrator, or if the list is public and you want to add yourself.

### Remove a member from a list

`DELETE /lists/{name}/members/{member}?type={type}`

* `type`: Can only be "user", "email", "list", or in rare cases, "kerberos". Default "user".

Errors:

* 200: successfully deleted
* 404: list does not exist
* 403: permission denied (not self or membership administrator)
* 400: invalid input - for instance, tried to delete someone who is not in the list anyway

### Get everything this list can administer

`GET /lists/{name}/belongings`

See documentation for `GET /users/{name}/belongings` -- same output

Get parameters:

* `recurse`: bool. Whether to include objects this list can administer because it is in a list that can administer it (and so on), as opposed to a direct ownership. Defaults to true.

Output:

```ts
[
    {
        "type": "list" | "machine" | "filesys" | ... ,
        "name": string,
    },
]
```

### Get lists this list is in

`GET /lists/{name}/lists`

Get parameters:

* `include_properties`: bool. Defaults to false. Whether to return properties of the mailing list apart from just the names

* `recurse`: bool. Whether to include the lists a user is in through other lists rather than just directly.

Output:

If `include_properties` is `false`, returns an array of strings representing the list names.

If `include_properties` is `true`, returns an array of list objects with `name`, `active`, `public`, `hidden`, `is_mailing_list`, `is_afs_group`.

For more details, see documentation for `GET /users/{name}/lists`

### Get administrator of the list

Get the administrator of the list. The administrator is allowed to change the details of the list, the membership list, and can remove it.

`GET /lists/{name}/owner`

Returns:

```ts
{
    "type": 'user' | 'list' | 'kerberos',
    "name": string,
}
```

NOTE: you should not need this query, because `GET /lists/{name}` already returns this

### Set administrator of the list

`PUT /lists/{name}/owner`

Input (as JSON body):

* `type`: The type of member ("user", "list" or "kerberos")
* `name`: The new administrator of this list

Returns the string "success" if successful

### Get membership administrator of the list

Get the membership administrator of the list. The membership administrator of the list can only add and remove members to the list, but cannot delete its attributes or delete the list.

`GET /lists/{name}/membership_admin`

Returns:

```ts
{
    "type": 'user' | 'list' | 'kerberos',
    "name": string,
}
```

NOTE: you should not need this query, because `GET /lists/{name}` already returns this

### Set membership administrator of the list

`PUT /lists/{name}/membership_admin`

Input (as JSON body):

* `type`: The type of member ("user", "list" or "kerberos")
* `name`: The new administrator of this list

Returns the string "success" if successful

### Delete membership administrator of the list

`DELETE /lists/{name}/membership_admin`

Deletes the membership admin of this list

## PO Boxes (i.e. mail forwarding)

TODO: define spec and implement

## Finger

### Get finger

`GET /users/me/finger`

Get my `finger` info, kept just like on the Moira query. Returns a single dictionary whose keys and values are strings. Values may be anything, 

The returned keys are:

* `affiliation`: Your "affiliation". For undergrads it seems to be the class year.
* `department`: Your department, seems to be the course number.
* `fullname`: Full name, which may or may not be the WebSIS name. This backend will be used to make a tool to let people change their name, while we try to get IS&T to sort that out. Clients must not display this other than for making ways to let people see and change finger info, otherwise you must use the name in `/users/me`
* `home_addr`: Home address, which seems to be synced from housing (wow! Even with StarREZ!)
* `home_phone`: Empty string in the case for undergrads
* `login`: Kerb/username
* `modby`: who modified finger last
* `modtime`: when this finger was last modified, in format "dd-mmm-yyyy hh:mm:ss"
* `modwith`: what tool or script finger was last modified with
* `nickname`: nickname?
* `office_addr`: office address
* `office_phone`: office phone

### Update finger

`PATCH /users/me/finger`

Input should be a JSON with any subset of the following parameters: `fullname`, `nickname`, `home_addr`, `home_phone`, `office_addr`, `office_phone`, `department`, `affiliation`

If they are ommitted or set to null, it means those attributes should not be modified.

Only pass as input those parameters you wish to modify.
