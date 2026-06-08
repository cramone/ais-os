-- EXPORT FOLDER

SELECT CONCAT(
    '{"path":"',
    STRING_ESCAPE(
        TRIM(
            REPLACE(
                REPLACE(
                    REPLACE(FOLDER_PATH, '\', '/'),
                    CHAR(13), ''
                ),
                CHAR(10), ''
            )
        ),
        'json'
    ),
    '","description":',
    CASE
        WHEN TRIM(ISNULL(FOLDER_DESCRIPTION, '')) IN ('', '0')
            THEN 'null'
        ELSE '"' + STRING_ESCAPE(TRIM(FOLDER_DESCRIPTION), 'json') + '"'
    END,
    ',"openedDate":',
    CASE
        WHEN FOLDER_REGISTERDATE IS NULL THEN 'null'
        ELSE '"' + CONVERT(varchar(40), CAST(FOLDER_REGISTERDATE AS datetime2(7)), 126) + '"'
    END,
    ',"originator":',
    CASE
        WHEN TRIM(ISNULL(FOLDER_OWNER, '')) = ''
            THEN 'null'
        ELSE '"' + STRING_ESCAPE(TRIM(FOLDER_OWNER), 'json') + '"'
    END,
    '}'
) AS JsonLine
FROM dbo.MEDIA_FOLDERS;