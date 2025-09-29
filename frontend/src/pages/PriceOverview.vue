<template>
    <div class="wrapper">
        <h1>各類商品物價概覽</h1>
        <h3 v-if="!isLoading" class="subtitle">資料更新時間：{{updateTime}}</h3>
        <div class="prices">
            <CategoryPrice 
                v-for="category in categoryList" 
                :key="category"
                class="category"
                :category="category" 
                :is-loading="isLoading" 
                :error-message="errorMessage" 
                :price-data="getPriceData(category)"></CategoryPrice>
        </div>
    </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import CategoryPrice from '@/components/CategoryPrice.vue';
import Categories from '@/constants/categories';
import { usePricesStore } from '@/stores/prices';

const store = usePricesStore();

const categoryList = computed(() => Object.keys(Categories));
const isLoading = computed(() => store.isLoading);
const errorMessage = computed(() => store.errorMessage);
const updateTime = computed(() => store.updatedTime);

function getPriceData(category) {
    return store.getPricesByCategory(category);
}

onMounted(() => {
    store.fetchPrices();
});
</script>

<style scoped>
.wrapper{
    padding: 3em 1em;
    background: #f3f3f3;
    min-height: calc(100vh - 4.5em);
    height: calc(100% - 4.5em);
    box-sizing: border-box;
}

@media (min-width: 768px) {
    .wrapper {
        padding: 3em 5em;
    }
}
.prices{
    display: flex;
    justify-content: space-around;
    flex-wrap: wrap;
}
.category{
    margin: 1em;
    flex-grow: 1;
}
.subtitle{
    font-weight: normal;
    margin-top: .5em;
}
</style>