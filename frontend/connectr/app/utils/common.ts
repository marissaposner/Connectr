export function classNames(...classes) {
    return classes.filter(Boolean).join(" ");
  }

export function getColours() {
  return [
    ['bg-green-50 text-green-700'],
    ['bg-red-50 text-red-700'],
    ['bg-yellow-50 text-yellow-700'],
    ['bg-blue-50 text-blue-700'],
    ['bg-orange-50 text-orange-700'],
    ['bg-rose-50 text-rose-700'],
  ]
}

export function getRandomArbitrary(min : number, max : number) {
  return Math.floor(Math.random() * (max - min) + min);
}