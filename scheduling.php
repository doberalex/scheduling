<?php

$people = [
    "Александр Б.",
    "Алексей Б.",
    "Андрей К.",
    "Вадим Б.",
    "Владимир П.",
    "Давид С.",
    "Давид Х.",
    "Дмитрий К.",
//    "Иван П.",
    "Махмуд Х.",
    "Петр С.",
    "Рустам М.",
    "Рустем Х.",
    "Александр Т.",
    "Самир Х.",
    "Наиль",
    "Артур Б.",
    "Тимур Х.",
];

function getRequestInt($name, $default, $min, $max)
{
    $value = isset($_GET[$name]) ? (int)$_GET[$name] : $default;
    
    if ($value < $min || $value > $max) {
        return $default;
    }
    
    return $value;
}

function buildMonthSlots($year, $month)
{
    $slots = [];
    $slotDates = [];
    $date = new DateTime(sprintf("%04d-%02d-01", $year, $month));
    $lastDay = (int)$date->format("t");
    $slotId = 1;
    
    for ($day = 1; $day <= $lastDay; $day++) {
        $date->setDate($year, $month, $day);
        $weekDay = (int)$date->format("N");
        
        if ($weekDay == 5) {
            $slots[$slotId] = "fri";
            $slotDates[$slotId] = $date->format("d.m.Y");
            $slotId++;
        } elseif ($weekDay == 7) {
            $slots[$slotId] = "sun";
            $slotDates[$slotId] = $date->format("d.m.Y");
            $slotId++;
        }
    }
    
    return [$slots, $slotDates];
}

$year = getRequestInt("year", (int)date("Y"), 2000, 2100);
$month = getRequestInt("month", (int)date("n"), 1, 12);
list($slots, $slotDates) = buildMonthSlots($year, $month);
$monthSeed = crc32(sprintf("%04d-%02d", $year, $month));

$limits = ["fri" => 3, "sun" => 5];

$blockedStart = [
//    "Александр Б.",
    "Алексей Б.",
    "Андрей К.",
    "Вадим Б.",
    "Владимир П.",
//    "Давид С.",
//    "Давид Х.",
//    "Дмитрий К.",
//    "Иван П.",
    "Махмуд Х.",
//    "Петр С.",
    "Рустам М.",
//    "Рустем Х.",
//    "Александр Т.",
//    "Самир Х.",
    "Наиль",
//    "Артур Б."
//    "Тимур Х.",
];

$singleParticipation = [
    "Петр С.",
    "Тимур Х.",
];

$onlySunday = [
    "Наиль",
    "Артур Б.",
    "Александр Б.",
];

$schedule = array_fill(1, 9, []);
$personSlots = [];

/**
 * Проверка интервала ≥3
 */
function validInterval($slotsList, $newSlot)
{
    foreach ($slotsList as $s) {
        if (abs($s - $newSlot) < 3) {
            return false;
        }
    }
    return true;
}

function getMaxParticipation($person, $singleParticipation)
{
    return in_array($person, $singleParticipation) ? 1 : 3;
}

function needsBothSlotTypes($person, $singleParticipation, $onlySunday)
{
    return getMaxParticipation($person, $singleParticipation) > 1 && !in_array($person, $onlySunday);
}

function getPersonSlotTypes($slotsList, $slots)
{
    $types = [];
    
    foreach ($slotsList as $slotId) {
        $types[$slots[$slotId]] = true;
    }
    
    return $types;
}

function validPersonSlotTypes($person, $slotsList, $slots, $singleParticipation, $onlySunday)
{
    if (!needsBothSlotTypes($person, $singleParticipation, $onlySunday)) {
        return true;
    }
    
    if (count($slotsList) < 2) {
        return false;
    }
    
    $types = getPersonSlotTypes($slotsList, $slots);
    
    return isset($types["fri"]) && isset($types["sun"]);
}

/**
 * Можно ли назначить
 */
function canAssign($person, $slotId, $personSlots, $slots, $schedule, $limits, $blockedStart, $singleParticipation, $onlySunday)
{
    if (in_array($person, $blockedStart) && in_array($slotId, [1, 2])) {
        return false;
    }
    
    if (in_array($person, $onlySunday) && $slots[$slotId] !== "sun") {
        return false;
    }
    
    $current = $personSlots[$person] ?? [];
    
    if (count($current) >= getMaxParticipation($person, $singleParticipation)) {
        return false;
    }
    
    if (!validInterval($current, $slotId)) {
        return false;
    }
    
    if (in_array($person, $schedule[$slotId])) {
        return false;
    }
    
    if (count($schedule[$slotId]) >= $limits[$slots[$slotId]]) {
        return false;
    }
    
    return true;
}

/**
 * BUILD
 */
function getBaseSlotLimits($slots, $limits)
{
    $slotLimits = [];
    
    foreach ($slots as $slotId => $type) {
        $slotLimits[$slotId] = $limits[$type];
    }
    
    return $slotLimits;
}

function createEmptySchedule($slots)
{
    $schedule = [];
    
    foreach ($slots as $slotId => $type) {
        $schedule[$slotId] = [];
    }
    
    return $schedule;
}

function createEmptyPersonSlots($people)
{
    $personSlots = [];
    
    foreach ($people as $person) {
        $personSlots[$person] = [];
    }
    
    return $personSlots;
}

function canAssignWithSlotLimits($person, $slotId, $personSlots, $slots, $schedule, $slotLimits, $blockedStart, $singleParticipation, $onlySunday)
{
    if (in_array($person, $blockedStart) && in_array($slotId, [1, 2])) {
        return false;
    }
    
    if (in_array($person, $onlySunday) && $slots[$slotId] !== "sun") {
        return false;
    }
    
    $current = $personSlots[$person] ?? [];
    
    if (count($current) >= getMaxParticipation($person, $singleParticipation)) {
        return false;
    }
    
    if (!validInterval($current, $slotId)) {
        return false;
    }
    
    if (in_array($person, $schedule[$slotId])) {
        return false;
    }
    
    if (count($schedule[$slotId]) >= $slotLimits[$slotId]) {
        return false;
    }
    
    return true;
}

function compareCandidates($a, $b, $personSlots)
{
    $countA = isset($personSlots[$a]) ? count($personSlots[$a]) : 0;
    $countB = isset($personSlots[$b]) ? count($personSlots[$b]) : 0;
    
    if ($countA != $countB) {
        return $countA - $countB;
    }
    
    return strcmp($a, $b);
}

function seededRank($value, $seed)
{
    return crc32($seed . "|" . $value);
}

function basicCanUseSlot($person, $slotId, $slots, $blockedStart, $onlySunday)
{
    if (in_array($person, $blockedStart) && in_array($slotId, [1, 2])) {
        return false;
    }
    
    if (in_array($person, $onlySunday) && $slots[$slotId] !== "sun") {
        return false;
    }
    
    return true;
}

function getAllowedSlotsForPerson($person, $slots, $blockedStart, $onlySunday)
{
    $allowed = [];
    
    foreach ($slots as $slotId => $type) {
        if (basicCanUseSlot($person, $slotId, $slots, $blockedStart, $onlySunday)) {
            $allowed[] = $slotId;
        }
    }
    
    return $allowed;
}

function generateSlotCombinations($allowedSlots, $maxCount, $startIndex = 0, $current = [])
{
    $combinations = [];
    
    if (!empty($current)) {
        $combinations[] = $current;
    }
    
    if (count($current) >= $maxCount) {
        return $combinations;
    }
    
    for ($i = $startIndex; $i < count($allowedSlots); $i++) {
        $slotId = $allowedSlots[$i];
        
        if (!validInterval($current, $slotId)) {
            continue;
        }
        
        $next = $current;
        $next[] = $slotId;
        
        foreach (generateSlotCombinations($allowedSlots, $maxCount, $i + 1, $next) as $combination) {
            $combinations[] = $combination;
        }
    }
    
    return $combinations;
}

function getPersonOptions($person, $slots, $blockedStart, $singleParticipation, $onlySunday, $seed)
{
    $maxCount = getMaxParticipation($person, $singleParticipation);
    $allowedSlots = getAllowedSlotsForPerson($person, $slots, $blockedStart, $onlySunday);
    $options = [];
    
    foreach (generateSlotCombinations($allowedSlots, $maxCount) as $combination) {
        $count = count($combination);
        
        if (in_array($person, $singleParticipation)) {
            if ($count == 1) {
                $options[] = $combination;
            }
            
            continue;
        }
        
        if (in_array($person, $onlySunday)) {
            $options[] = $combination;
            continue;
        }
        
        if ($count >= 2 && validPersonSlotTypes($person, $combination, $slots, $singleParticipation, $onlySunday)) {
            $options[] = $combination;
        }
    }
    
    usort($options, function ($a, $b) use ($person, $seed) {
        $countCompare = count($b) - count($a);
        
        if ($countCompare != 0) {
            return $countCompare;
        }
        
        return seededRank($person . ":" . implode(",", $a), $seed) - seededRank($person . ":" . implode(",", $b), $seed);
    });
    
    return $options;
}

function optionFitsRemaining($option, $remaining)
{
    $used = [];
    
    foreach ($option as $slotId) {
        $used[$slotId] = ($used[$slotId] ?? 0) + 1;
        
        if ($used[$slotId] > $remaining[$slotId]) {
            return false;
        }
    }
    
    return true;
}

function subtractOptionFromRemaining($option, $remaining)
{
    foreach ($option as $slotId) {
        $remaining[$slotId]--;
    }
    
    return $remaining;
}

function remainingTotal($remaining)
{
    return array_sum($remaining);
}

function maxAssignableFromIndex($people, $optionsByPerson, $index)
{
    $total = 0;
    
    for ($i = $index; $i < count($people); $i++) {
        $person = $people[$i];
        $max = 0;
        
        foreach ($optionsByPerson[$person] as $option) {
            $max = max($max, count($option));
        }
        
        $total += $max;
    }
    
    return $total;
}

function solveByPersonOptions($people, $optionsByPerson, $remaining, &$personSlots, $index = 0)
{
    if ($index >= count($people)) {
        return remainingTotal($remaining) == 0;
    }
    
    if (remainingTotal($remaining) > maxAssignableFromIndex($people, $optionsByPerson, $index)) {
        return false;
    }
    
    $person = $people[$index];
    
    foreach ($optionsByPerson[$person] as $option) {
        if (!optionFitsRemaining($option, $remaining)) {
            continue;
        }
        
        $personSlots[$person] = $option;
        
        if (solveByPersonOptions($people, $optionsByPerson, subtractOptionFromRemaining($option, $remaining), $personSlots, $index + 1)) {
            return true;
        }
        
        $personSlots[$person] = [];
    }
    
    return false;
}

function buildScheduleFromPersonSlots($personSlots, $slots)
{
    $schedule = createEmptySchedule($slots);
    
    foreach ($personSlots as $person => $personSlotList) {
        foreach ($personSlotList as $slotId) {
            $schedule[$slotId][] = $person;
        }
    }
    
    return $schedule;
}

function tryBuildScheduleByPersonOptions($people, $slots, $slotLimits, $blockedStart, $singleParticipation, $onlySunday, $seed, &$schedule, &$personSlots)
{
    $optionsByPerson = [];
    
    foreach ($people as $person) {
        $options = getPersonOptions($person, $slots, $blockedStart, $singleParticipation, $onlySunday, $seed);
        
        if (empty($options)) {
            return false;
        }
        
        $optionsByPerson[$person] = $options;
    }
    
    $orderedPeople = $people;
    usort($orderedPeople, function ($a, $b) use ($optionsByPerson, $seed) {
        $countCompare = count($optionsByPerson[$a]) - count($optionsByPerson[$b]);
        
        if ($countCompare != 0) {
            return $countCompare;
        }
        
        return seededRank($a, $seed) - seededRank($b, $seed);
    });
    
    $personSlots = createEmptyPersonSlots($people);
    
    if (!solveByPersonOptions($orderedPeople, $optionsByPerson, $slotLimits, $personSlots)) {
        return false;
    }
    
    $schedule = buildScheduleFromPersonSlots($personSlots, $slots);
    
    return true;
}

function findNextSlot($schedule, $personSlots, $people, $slots, $slotLimits, $blockedStart, $singleParticipation, $onlySunday, &$slotCandidates)
{
    $bestSlotId = null;
    $bestCandidates = [];
    
    foreach ($slots as $slotId => $type) {
        if (count($schedule[$slotId]) >= $slotLimits[$slotId]) {
            continue;
        }
        
        $candidates = [];
        
        foreach ($people as $person) {
            if (canAssignWithSlotLimits($person, $slotId, $personSlots, $slots, $schedule, $slotLimits, $blockedStart, $singleParticipation, $onlySunday)) {
                $candidates[] = $person;
            }
        }
        
        usort($candidates, function ($a, $b) use ($personSlots) {
            return compareCandidates($a, $b, $personSlots);
        });
        
        if ($bestSlotId === null || count($candidates) < count($bestCandidates)) {
            $bestSlotId = $slotId;
            $bestCandidates = $candidates;
            
            if (empty($bestCandidates)) {
                break;
            }
        }
    }
    
    $slotCandidates = $bestCandidates;
    
    return $bestSlotId;
}

function scheduleTypesArePossible($personSlots, $people, $slots, $singleParticipation, $onlySunday)
{
    foreach ($people as $person) {
        if (!needsBothSlotTypes($person, $singleParticipation, $onlySunday)) {
            continue;
        }
        
        $list = $personSlots[$person] ?? [];
        $maxParticipation = getMaxParticipation($person, $singleParticipation);
        
        if (count($list) >= $maxParticipation && !validPersonSlotTypes($person, $list, $slots, $singleParticipation, $onlySunday)) {
            return false;
        }
    }
    
    return true;
}

function finalScheduleTypesAreValid($personSlots, $people, $slots, $singleParticipation, $onlySunday)
{
    foreach ($people as $person) {
        $list = $personSlots[$person] ?? [];
        
        if (empty($list)) {
            continue;
        }
        
        if (!validPersonSlotTypes($person, $list, $slots, $singleParticipation, $onlySunday)) {
            return false;
        }
    }
    
    return true;
}

function fillScheduleRecursive(&$schedule, &$personSlots, $people, $slots, $slotLimits, $blockedStart, $singleParticipation, $onlySunday)
{
    $candidates = [];
    $slotId = findNextSlot($schedule, $personSlots, $people, $slots, $slotLimits, $blockedStart, $singleParticipation, $onlySunday, $candidates);
    
    if ($slotId === null) {
        return finalScheduleTypesAreValid($personSlots, $people, $slots, $singleParticipation, $onlySunday);
    }
    
    if (empty($candidates)) {
        return false;
    }
    
    foreach ($candidates as $person) {
        $schedule[$slotId][] = $person;
        $personSlots[$person][] = $slotId;
        
        if (
            scheduleTypesArePossible($personSlots, $people, $slots, $singleParticipation, $onlySunday)
            && fillScheduleRecursive($schedule, $personSlots, $people, $slots, $slotLimits, $blockedStart, $singleParticipation, $onlySunday)
        ) {
            return true;
        }
        
        array_pop($schedule[$slotId]);
        array_pop($personSlots[$person]);
    }
    
    return false;
}

function buildSchedule($people, $slots, $limits, $blockedStart, $singleParticipation, $onlySunday, $seed, &$resolvedSlotLimits)
{
    $baseSlotLimits = getBaseSlotLimits($slots, $limits);
    $variants = [$baseSlotLimits];
    
    foreach ($slots as $slotId => $type) {
        if ($baseSlotLimits[$slotId] <= 0) {
            continue;
        }
        
        $variant = $baseSlotLimits;
        $variant[$slotId]--;
        $variants[] = $variant;
    }
    
    foreach ($variants as $slotLimits) {
        $schedule = createEmptySchedule($slots);
        $personSlots = createEmptyPersonSlots($people);
        
        if (tryBuildScheduleByPersonOptions($people, $slots, $slotLimits, $blockedStart, $singleParticipation, $onlySunday, $seed, $schedule, $personSlots)) {
            $resolvedSlotLimits = $slotLimits;
            return [$schedule, $personSlots];
        }
        
        if (fillScheduleRecursive($schedule, $personSlots, $people, $slots, $slotLimits, $blockedStart, $singleParticipation, $onlySunday)) {
            $resolvedSlotLimits = $slotLimits;
            return [$schedule, $personSlots];
        }
    }
    
    $resolvedSlotLimits = $baseSlotLimits;
    return [createEmptySchedule($slots), createEmptyPersonSlots($people)];
}

$resolvedSlotLimits = [];
list($schedule, $personSlots) = buildSchedule($people, $slots, $limits, $blockedStart, $singleParticipation, $onlySunday, $monthSeed, $resolvedSlotLimits);

function validateSchedule($schedule, $personSlots, $slots, $limits, $blockedStart, $singleParticipation, $onlySunday)
{
    $errors = [];
    
    foreach ($schedule as $slotId => $list) {
        $type = $slots[$slotId];
        $expected = $limits[$type];
        
        if (count($list) != $expected) {
            $errors[] = "Слот {$slotId}: назначено " . count($list) . " из {$expected}";
        }
        
        if (count($list) != count(array_unique($list))) {
            $errors[] = "Слот {$slotId}: есть повтор участника";
        }
        
        foreach ($list as $person) {
            if (in_array($person, $blockedStart) && in_array($slotId, [1, 2])) {
                $errors[] = "{$person}: запрещён слот {$slotId}";
            }
            
            if (in_array($person, $onlySunday) && $type !== "sun") {
                $errors[] = "{$person}: разрешено только воскресенье, найден слот {$slotId}";
            }
        }
    }
    
    foreach ($personSlots as $person => $list) {
        sort($list);
        
        $maxParticipation = getMaxParticipation($person, $singleParticipation);
        
        if (count($list) > $maxParticipation) {
            $errors[] = "{$person}: больше {$maxParticipation} участий";
        }
        
        if (!empty($list) && !validPersonSlotTypes($person, $list, $slots, $singleParticipation, $onlySunday)) {
            $errors[] = "{$person}: должны быть участия и в пятницу, и в воскресенье";
        }
        
        foreach ($list as $i => $slotId) {
            foreach ($list as $j => $compareSlotId) {
                if ($j <= $i) {
                    continue;
                }
                
                if (abs($slotId - $compareSlotId) < 3) {
                    $errors[] = "{$person}: нарушен интервал между слотами {$slotId} и {$compareSlotId}";
                }
            }
        }
    }
    
    return $errors;
}

function getStartCapacityError($people, $slots, $limits, $blockedStart, $onlySunday)
{
    $needed = $limits[$slots[1]] + $limits[$slots[2]];
    $available = [];
    
    foreach ($people as $person) {
        $canUseStart = false;
        
        foreach ([1, 2] as $slotId) {
            if (in_array($person, $blockedStart) && in_array($slotId, [1, 2])) {
                continue;
            }
            
            if (in_array($person, $onlySunday) && $slots[$slotId] !== "sun") {
                continue;
            }
            
            $canUseStart = true;
        }
        
        if ($canUseStart) {
            $available[] = $person;
        }
    }
    
    if (count($available) >= $needed) {
        return null;
    }
    
    return "Слоты 1 и 2 требуют {$needed} разных участников, доступно только " . count($available) . ": " . implode(", ", $available);
}

/**
 * OUTPUT
 */

echo "<pre>";
echo "Месяц: " . sprintf("%02d.%04d", $month, $year) . "\n";
echo "Слоты:\n";

foreach ($slots as $slotId => $type) {
    echo "[{$slotId}] => {$slotDates[$slotId]} ({$type})\n";
}

echo "\n";
print_r($schedule);

$errors = validateSchedule($schedule, $personSlots, $slots, $limits, $blockedStart, $singleParticipation, $onlySunday);
$startCapacityError = getStartCapacityError($people, $slots, $limits, $blockedStart, $onlySunday);

if ($startCapacityError !== null) {
    $errors[] = $startCapacityError;
}

if (!empty($errors)) {
    echo "\nПроверка:\n";
    print_r($errors);
}

echo "</pre>";
