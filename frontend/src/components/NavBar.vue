<template>
    <nav class="navbar">
        <div class="title"> <RouterLink to="/overview">價格追蹤小幫手</RouterLink></div>
        <div class="hamburger" @click="toggleMenu">&#9776;</div>
        <ul class="options" :class="{ 'is-active': isMenuOpen }">
            <li><RouterLink to="/overview" @click="toggleMenu">物價概覽</RouterLink></li>
            <li><RouterLink to="/trending" @click="toggleMenu">物價趨勢</RouterLink></li>
            <li><RouterLink to="/news" @click="toggleMenu">相關新聞</RouterLink></li>
            <li v-if="!isLoggedIn"><RouterLink to="/login" @click="toggleMenu">登入</RouterLink></li>
            <li v-else @click="logout, toggleMenu">Hi, {{getUserName}}! 登出</li>
        </ul>
    </nav>
</template>

<script>
import { useAuthStore } from '@/stores/auth';

export default {
    name: 'NavBar',
    data() {
        return {
            isMenuOpen: false,
        };
    },
    computed: {
        isLoggedIn(){
            const userStore = useAuthStore();
            return userStore.isLoggedIn;
        },
        getUserName(){
            const userStore = useAuthStore();
            return userStore.getUserName;
        }
    },
    methods: {
        toggleMenu() {
            this.isMenuOpen = !this.isMenuOpen;
        },
        logout(){
            const userStore = useAuthStore();
            userStore.logout();
        }
    }
};
</script>

<style scoped>
.navbar {
    display: flex;
    justify-content: space-between;
    background-color: #f3f3f3;
    padding: 1.5em;
    height: 4.5em;
    width: 100%;
    align-items: center;
    box-shadow: 0 0 5px #000000;
}

.navbar ul {
    list-style: none;
    justify-content: space-around;
}

.hamburger {
    display: none;
    font-size: 2em;
    cursor: pointer;
}

/* 2025/9/25 HW3 Task1 start */
@media (max-width: 767px) {
    .navbar ul {
        display: none;
        position: absolute;
        top: 4.5em;
        left: 0;
        background-color: #f3f3f3;
        width: 100%;
        flex-direction: column;
        align-items: center;
        box-shadow: 0 5px 5px -5px #000000;
    }
    .navbar ul.is-active {
        display: flex;
    }
    .navbar ul li {
        padding: 1em 0;
    }
    .hamburger {
        display: block;
    }
}

@media (min-width: 768px){
    .navbar ul { display: flex; }
}
/* 2025/9/25 HW3 Task1 end */

.title > a{
    font-size: 1.4em;
    font-weight: bold;
    color: #2c3e50 !important;
}

.navbar li {
    color: #575B5D;
    margin: 0 .5em;
    font-size: 1.2em;
}

.navbar li:hover{
    cursor: pointer;
    font-weight: bold;
}

.navbar a {
    text-decoration: none;
    color: #575B5D;
}

</style>