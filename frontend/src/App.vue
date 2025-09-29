<template>
  <NavBar class="navbar"></NavBar>
  <router-view v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" class="render" />
    </transition>
  </router-view>
</template>

<script setup>
// import { RouterView } from 'vue-router';
import NavBar from './components/NavBar.vue'
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
}
.navbar{
  z-index: 1000;
  position: fixed;
  top: 0;
}
.render{
  margin-top: 4.5em;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
