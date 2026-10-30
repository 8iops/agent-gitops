# Consume untrusted native stdout without retaining keys, values or log lines.
$0 == "> \\x00\\x00\\x00\\x06" { schema = 6 }
/^p.* : / { records++ }
END {
    if (schema == 6 && records > 1) {
        printf "{\"nativeReadability\":\"pass\",\"schemaVersion\":6,\"propertyRecords\":%d}\n", records
        exit 0
    }
    print "{\"nativeReadability\":\"failed\"}"
    exit 1
}
