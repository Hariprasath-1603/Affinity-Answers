-- Question 1: How many types of Acacia plants can be found in the taxonomy table?

SELECT COUNT(*) AS total_acacia_types
FROM taxonomy
WHERE species LIKE '%Acacia%';
