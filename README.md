GET extensions to OpenStack Swift
=================================

Motivation
----------

Currently Swift is not optimal for storing billions of small files. This is a consequence of the fact that every object in Swift is a file on the underlying file system (not counting the replicas). Every file requires its metadata to be loaded into memory before it can be processed. Metadata is normally cached by the file system but when the total number of files is too large and access is fairly random caching no longer works and performance quickly degrades. The Swift's container or tenant catalogs held in sqlite databases don't offer stellar performance either when the number of items in them goes into millions.

An alternative for this use case could be a database such as HBase or Cassandra, which know how to deal with BLOBs. Databases have their ways to aggregate data in large files and then find it when necessary. However, database-as-storage have their own problems, one of which is added complexity.

The above patch offers a way around the Swift's limitation for one specific but important use case:

1. one needs to store many small(ish) files, say 1-100KB, which when stored separately cause performance degradation
2. these files don't change (too often) such as in data warehouse
3. a random access to the files is necessary


Solution
--------

The solution implemented here is to aggregate the small files in archives, such as zip or tar, of reasonable size. The archives can only be written as a whole. They can, of course, be read as a whole with the existing Swift's GET command like (pseudocode):

`GET /tenant/container/big_file.zip`

The patch modifies the behavior of the command if additional parameters are present, for example:

`GET /tenant/container/big_file.zip?as=zip&list_content`

will result in plain/text response with a list of files in the zip

`GET /tenant/container/big_file.zip?as=zip&get_content=content_file1.png,content_file2.bin`

will bring a multipart response with the requested files as binary attachments

The additional GET functionality must be activated in the config file or there will be no change in Swift's behavior.

The total size of attachments is limited to prevent "explosion" attack when decompressing files.
