-- Question 2: Which type of wheat has the longest DNA sequence?

SELECT 
    t.species,
    MAX(r.length) AS longest_sequence
FROM rfamseq r
JOIN taxonomy t ON r.ncbi_id = t.ncbi_id
WHERE t.species LIKE '%wheat%'
   OR t.tax_string LIKE '%Triticum%'
GROUP BY t.species
ORDER BY longest_sequence DESC
LIMIT 1;
