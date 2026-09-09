<script setup>
defineProps({ type: { type: String, default: 'info' }, message: { type: String, required: true } })
</script>

<template><div class="status-message" :class="`status-${type}`" role="status">{{ message }}</div></template>
