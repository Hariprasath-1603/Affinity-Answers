#!/usr/bin/env bash

# S&P 500 dataset source and output
URL="https://raw.githubusercontent.com/datasets/s-and-p-500-companies/refs/heads/main/data/constituents.csv"
OUTPUT_FILE="sorted_company.csv"

echo "Downloading and processing company data..."

# Temporary file for intermediate tab-delimited records
TMP_FILE=$(mktemp)

# Fetch CSV, extract Company Name ($2), Location ($5), and Founding Year ($8),
# then sort chronologically by year
curl -sSL "$URL" | tr -d '\r' | awk -v FPAT='("[^"]*")|([^,]+)' '
    NR > 1 {
        name = $2
        location = $5
        year = $8

        # Strip surrounding quotes
        gsub(/^"|"$/, "", name)
        gsub(/^"|"$/, "", location)
        gsub(/^"|"$/, "", year)

        if (name != "") {
            print name "\t" location "\t" year
        }
    }
' | sort -t$'\t' -k3,3n > "$TMP_FILE"

# Write header to output CSV
echo "Company Name,Location,Founding Year" > "$OUTPUT_FILE"

# Append records, quoting fields that contain commas
while IFS=$'\t' read -r name location year; do
    [[ "$name" == *","* ]] && name="\"$name\""
    [[ "$location" == *","* ]] && location="\"$location\""
    [[ "$year" == *","* ]] && year="\"$year\""

    echo "$name,$location,$year" >> "$OUTPUT_FILE"
done < "$TMP_FILE"

# Clean up
rm -f "$TMP_FILE"

echo "Successfully saved sorted data to $OUTPUT_FILE"

