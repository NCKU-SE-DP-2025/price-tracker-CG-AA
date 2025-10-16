<template>
    <div class="trending-table">
        <table>
            <thead>
                <tr>
                    <th rowspan="2">年份</th>
                    <th v-for="month in months" :key="month">{{ month }}</th>
                </tr>
            </thead>
            <tbody>
                <template v-for="year in years" :key="year">
                    <tr>
                        <td>{{ year }}</td>
                        <template v-for="(value, monthIndex) in getYearData(year)" :key="year + '-month-' + monthIndex">
                            <td>{{ valueDisplay(value) }}</td>
                        </template>
                    </tr>
                </template>
            </tbody>
        </table>
    </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';

const props = defineProps({
    data: {
        type: Object,
        required: true
    }
});

const yearData = ref({});

const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const years = computed(() => {
    if (!props.data || !props.data.時間起點 || !props.data.時間終點) return [];
    const startYear = new Date(props.data.時間起點).getFullYear();
    const endYear = new Date(props.data.時間終點).getFullYear();
    let years = [];
    for (let year = startYear; year <= endYear; year++) {
        years.push(year);
    }
    return years;
});

function getYearData(year) {
    return yearData.value[year];
}

function processInitData() {
    if (!props.data || !props.data.時間起點 || !props.data.時間終點) return;
    const startMonth = new Date(props.data.時間起點).getMonth() + 1;
    const endMonth = new Date(props.data.時間終點).getMonth() + 1;
    const startYear = new Date(props.data.時間起點).getFullYear();
    const endYear = new Date(props.data.時間終點).getFullYear();
    const newYearData = {};
    for (let year = startYear; year <= endYear; year++) {
        let yearPrices = [];
        for (let month = 1; month <= 12; month++) {
            if (year === startYear && month < startMonth) {
                yearPrices.push('0');
            } else if (year === endYear && month > endMonth) {
                yearPrices.push('0');
            } else {
                const index = month + (year - startYear) * 12 - startMonth;
                const prices = props.data.統計值.split(',');
                yearPrices.push(prices[index] || '0');
            }
        }
        newYearData[year] = yearPrices;
    }
    yearData.value = newYearData;
}

function valueDisplay(value) {
    return value === '0' ? '-' : value;
}

watch(() => props.data, (newVal) => {
    if (newVal) {
        processInitData();
    }
}, { deep: true });

onMounted(() => {
    processInitData();
});
</script>

<style scoped>
.trending-table {
    margin-top: 2em;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th,
td {
    border: 1px solid #ccc;
    padding: 0.5em;
    text-align: center;
}
</style>