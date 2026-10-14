-- Question 3 & 4: Paginated list of families with longest DNA sequence > 1,000,000
-- Page 9 with 15 results per page -> OFFSET 120

SELECT 
    f.rfam_acc,
    f.rfam_id,
    MAX(r.length) AS max_seq_length
FROM family f
JOIN full_region fr ON f.rfam_acc = fr.rfam_acc
JOIN rfamseq r ON fr.rfamseq_acc = r.rfamseq_acc
GROUP BY f.rfam_acc, f.rfam_id
HAVING MAX(r.length) > 1000000
ORDER BY max_seq_length DESC
LIMIT 15 OFFSET 120;
